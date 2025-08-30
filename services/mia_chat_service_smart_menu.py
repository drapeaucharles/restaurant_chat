"""
Smart Menu MIA Chat Service - Fetches specific dish details on demand
Only provides detailed information when explicitly requested
"""
import requests
import json
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import models
from schemas.chat import ChatRequest, ChatResponse
import os
import logging
from services.mia_chat_service_hybrid import get_mia_response_hybrid
from services.customer_memory_service import CustomerMemoryService

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def extract_dish_name(message: str, menu_items: List[Dict]) -> Optional[Dict]:
    """Extract which dish the user is asking about"""
    message_lower = message.lower()
    
    # Check each menu item
    for item in menu_items:
        dish_name = (item.get('dish') or item.get('name', '')).lower()
        # Check if dish name is mentioned in the message
        if dish_name and dish_name in message_lower:
            return item
        # Check individual words for better matching
        dish_words = dish_name.split()
        if len(dish_words) > 1 and all(word in message_lower for word in dish_words):
            return item
    
    return None

def build_minimal_menu_context(menu_items: List[Dict]) -> str:
    """Build minimal menu context - just categories and dish names"""
    if not menu_items:
        return "\nNo menu information available."
    
    context_parts = ["Our menu categories:"]
    
    # Group by category
    categories = {}
    for item in menu_items:
        cat = item.get('category') or item.get('subcategory', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item.get('dish') or item.get('name', ''))
    
    # List just dish names by category
    for category, dishes in categories.items():
        context_parts.append(f"\n{category}: {', '.join(dishes)}")
    
    return "\n".join(context_parts)

def build_dish_detail_context(dish: Dict) -> str:
    """Build detailed context for a specific dish"""
    details = []
    
    name = dish.get('dish') or dish.get('name', 'This dish')
    details.append(f"Details for {name}:")
    
    if dish.get('description'):
        details.append(f"Description: {dish['description']}")
    
    if dish.get('ingredients'):
        details.append(f"Ingredients: {', '.join(dish['ingredients'])}")
    
    if dish.get('allergens'):
        details.append(f"Allergens: {', '.join(dish['allergens'])}")
    
    if dish.get('price'):
        details.append(f"Price: {dish['price']}")
    
    if dish.get('preparation'):
        details.append(f"Preparation: {dish['preparation']}")
    
    return "\n".join(details)

def mia_chat_service_smart_menu(req: ChatRequest, db: Session) -> ChatResponse:
    """Smart menu chat service - fetches dish details only when needed"""
    
    try:
        logger.info(f"SMART MENU SERVICE - Request: {req.message[:50]}...")
        
        # Skip AI for restaurant staff messages
        if req.sender_type == 'restaurant':
            return ChatResponse(answer="")
        
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
        
        data = restaurant.data or {}
        business_name = data.get('restaurant_name', req.restaurant_id)
        menu_items = data.get('menu', [])
        
        # Extract and update customer profile
        extracted_info = CustomerMemoryService.extract_customer_info(req.message)
        if extracted_info:
            profile = CustomerMemoryService.update_customer_profile(
                db, req.client_id, req.restaurant_id, extracted_info
            )
        else:
            # Get existing profile
            client_id_str = str(req.client_id)
            profile = db.query(models.CustomerProfile).filter(
                models.CustomerProfile.client_id == client_id_str,
                models.CustomerProfile.restaurant_id == req.restaurant_id
            ).first()
        
        # Get customer context
        customer_context = CustomerMemoryService.get_customer_context(profile)
        
        # Check if user is asking about a specific dish
        query_lower = req.message.lower()
        is_detail_request = any(phrase in query_lower for phrase in [
            'tell me more', 'tell me about', 'describe', 'what is', "what's in", 
            'how is it', 'details', 'ingredients', 'allergen', 'contain'
        ])
        
        # Find specific dish if mentioned
        specific_dish = extract_dish_name(req.message, menu_items) if is_detail_request else None
        
        # Build appropriate menu context
        if specific_dish:
            # User asking about specific dish - provide full details
            menu_context = build_minimal_menu_context(menu_items) + "\n\n" + build_dish_detail_context(specific_dish)
            system_prompt = f"""You are Maria, a friendly server at {business_name}.

The customer is asking about a specific dish. Provide comprehensive details including:
- Full description
- All ingredients 
- Allergens
- Price
- What makes it special
- Preparation method if relevant

Be warm and enthusiastic about the dish!"""
            # Use more tokens for detailed response
            params = {"temperature": 0.8, "max_tokens": 500}
        else:
            # General conversation - minimal menu context
            menu_context = build_minimal_menu_context(menu_items)
            system_prompt = f"""You are Maria, a friendly server at {business_name}.

Be warm but concise:
- Keep responses short (2-4 sentences max)
- Sound natural, not robotic
- Remember customer details from previous messages
- Use their name if they've told you
- If they ask about a dish, let them know you can provide full details"""
            params = {"temperature": 0.7, "max_tokens": 300}
        
        # Get recent chat history
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
        
        # Build conversation history
        chat_history = []
        for msg in reversed(recent_messages[1:]):  # Skip current message
            if msg.sender_type == "client":
                chat_history.append(f"Customer: {msg.message}")
            elif msg.sender_type == "ai":
                chat_history.append(f"Assistant: {msg.message}")
        
        history_text = "\n".join(chat_history[-6:]) if chat_history else ""
        
        # Build full prompt
        full_prompt = f"""{system_prompt}

{menu_context}

Customer Profile:
{customer_context}

Previous conversation:
{history_text}

Customer: {req.message}
Assistant:"""
        
        logger.info(f"Smart menu using {'detailed' if specific_dish else 'minimal'} context")
        
        # Get AI response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in smart_menu service: {str(e)}", exc_info=True)
        try:
            db.rollback()
        except:
            pass
        return ChatResponse(answer="I apologize, but I'm having technical difficulties. Please try again.")