"""
MIA Chat Service - Simplified version that works
"""
import requests
import re
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from pinecone_utils import query_pinecone
from schemas.chat import ChatRequest, ChatResponse
from schemas.restaurant import RestaurantData
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from services.restaurant_service import apply_menu_fallbacks
from services.simple_response_cache import response_cache
import os
import logging

logger = logging.getLogger(__name__)

# MIA Backend URL - can be configured via environment variable
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_LOCAL_URL = os.getenv("MIA_LOCAL_URL", "http://localhost:8001")

# System prompt
system_prompt = """
You are a friendly restaurant assistant. The customer is viewing our complete menu on their screen.

CRITICAL RULES:
1. If an item is NOT in the provided context, it's NOT on our menu - say "We don't have [item], but..."
2. When something isn't available, suggest a similar item from the context if possible
3. ONLY mention items explicitly provided in the context - these are our actual menu items
4. They can see the menu, so don't list everything
5. Be concise and helpful - max 2-3 sentences
6. For ingredients/allergens: only answer if you have the specific info, otherwise say you'll check
7. Always respond in the same language as the customer's message
"""

def get_mia_response_direct(prompt: str, max_tokens: int = 150) -> str:
    """Get response from MIA using direct API endpoint"""
    try:
        # First try local MIA instance
        try:
            response = requests.post(
                f"{MIA_LOCAL_URL}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "restaurant_mode": True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "I'm having trouble understanding. Could you please rephrase?")
        except:
            logger.info("Local MIA not available, trying remote")
        
        # Try remote MIA backend
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json={
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "source": "restaurant"
            },
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("text", result.get("response", "I'm having trouble understanding. Could you please rephrase?"))
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            return "I apologize, but I'm having technical difficulties. Please try again in a moment or ask our staff for assistance."
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "I'm taking a bit longer to respond. Please try again."
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}")
        return "I'm experiencing technical difficulties. Please try again or ask our staff for help."

def fetch_recent_chat_history(db: Session, client_id: str, restaurant_id: str):
    """Fetch recent chat history for context"""
    logger.info(f"Fetching chat history for client {client_id}, restaurant {restaurant_id}")
    
    cutoff_time = datetime.utcnow() - timedelta(minutes=60)
    
    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == client_id,
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.timestamp >= cutoff_time,
        models.ChatMessage.sender_type.in_(['client', 'ai'])
    ).order_by(models.ChatMessage.timestamp.asc()).limit(20).all()
    
    logger.info(f"Found {len(recent_messages)} recent messages for context")
    
    return recent_messages

def get_or_create_client(db: Session, client_id: str, restaurant_id: str, phone_number: str = None):
    """Get or create a client record."""
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        try:
            client = models.Client(
                id=client_id, 
                restaurant_id=restaurant_id,
                phone_number=phone_number
            )
            db.add(client)
            db.commit()
            db.refresh(client)
        except IntegrityError:
            db.rollback()
            client = db.query(models.Client).filter_by(id=client_id).first()
    else:
        if phone_number and not client.phone_number:
            client.phone_number = phone_number
            db.commit()
            db.refresh(client)
    return client

def format_menu_for_context(menu_items, query):
    """Format menu items for context - simple version"""
    if not menu_items:
        return "Menu data unavailable."
    
    query_lower = query.lower()
    context_lines = []
    
    # For general menu queries, show categories
    if any(word in query_lower for word in ['menu', 'serve', 'offer', 'have', 'dishes']):
        categories = {}
        for item in menu_items[:30]:  # Limit for performance
            cat = item.get('subcategory', 'main')
            if cat not in categories:
                categories[cat] = []
            name = item.get('name') or item.get('dish', '')
            if name:
                categories[cat].append(name)
        
        for cat, items in categories.items():
            if items:
                context_lines.append(f"{cat.title()}: {', '.join(items[:5])}")
    
    # For specific queries, find relevant items
    else:
        for item in menu_items[:20]:  # Limit search
            name = item.get('name') or item.get('dish', '')
            if not name:
                continue
                
            name_lower = name.lower()
            ingredients = item.get('ingredients', [])
            
            # Check relevance
            relevant = False
            if 'vegetarian' in query_lower or 'vegan' in query_lower:
                meat_keywords = ['beef', 'pork', 'chicken', 'duck', 'lamb', 'veal', 'bacon']
                if not any(meat in str(ingredients).lower() for meat in meat_keywords):
                    relevant = True
            elif any(word in name_lower for word in query_lower.split() if len(word) > 3):
                relevant = True
            elif any(word in str(ingredients).lower() for word in query_lower.split() if len(word) > 3):
                relevant = True
            
            if relevant:
                price = item.get('price', '')
                desc = item.get('description', '')[:50]
                context_lines.append(f"{name} ({price}): {desc}")
                if len(context_lines) >= 5:  # Limit results
                    break
    
    return "\n".join(context_lines) if context_lines else ""

def mia_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Handle chat requests using MIA backend - simplified version"""
    
    logger.info(f"MIA CHAT SERVICE - Restaurant: {req.restaurant_id}, Client: {req.client_id}")
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        logger.error(f"Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    # Check if this is a restaurant staff message
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Get restaurant data
    data = restaurant.data or {}
    
    try:
        # Get menu items
        menu_items = data.get("menu", [])
        if menu_items:
            try:
                menu_items = apply_menu_fallbacks(menu_items)
            except Exception as e:
                logger.warning(f"Error applying menu fallbacks: {e}")
        
        # Build context
        context_parts = [system_prompt]
        context_parts.append(f"\nRestaurant: {restaurant.restaurant_id}")
        context_parts.append(f"Customer asks: '{req.message}'")
        
        # Add menu context
        menu_context = format_menu_for_context(menu_items, req.message)
        if menu_context:
            context_parts.append("\nRelevant menu information:")
            context_parts.append(menu_context)
        
        # Add opening hours if asked
        if any(word in req.message.lower() for word in ['hour', 'open', 'close', 'when']):
            hours = data.get('opening_hours', {})
            if hours:
                context_parts.append(f"\nOpening hours: {hours}")
        
        # Final prompt
        full_prompt = "\n".join(context_parts)
        full_prompt += f"\n\nCustomer: {req.message}\nAssistant:"
        
        # Get response from MIA
        answer = get_mia_response_direct(full_prompt, max_tokens=150)
        
    except Exception as e:
        logger.error(f"Error in MIA chat service: {e}")
        answer = "I'm experiencing technical difficulties. Please try again later."
    
    # Save AI response
    new_message = models.ChatMessage(
        restaurant_id=req.restaurant_id,
        client_id=req.client_id,
        sender_type="ai",
        message=answer
    )
    db.add(new_message)
    db.commit()
    
    logger.info("MIA response processed successfully")
    
    return ChatResponse(answer=answer)