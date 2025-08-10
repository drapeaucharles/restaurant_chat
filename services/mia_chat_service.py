"""
MIA Chat Service - Clean simplified version
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
MIA_LOCAL_URL = os.getenv("MIA_LOCAL_URL", "http://localhost:8000")

# System prompt - UPDATED to be context-aware
system_prompt = """
You are a friendly restaurant assistant at a restaurant's digital menu interface.
When customers greet you, welcome them warmly and guide them naturally - they're likely here to explore the menu.
Suggest how you can help with menu questions, dietary needs, or recommendations.
Keep responses concise and helpful. Respond in the customer's language.
Don't list menu items unless specifically asked - instead offer to help them find what they're looking for.
"""

def get_mia_response_direct(prompt: str, max_tokens: int = 150) -> str:
    """Get response from MIA using direct API endpoint"""
    try:
        # TEMPORARILY DISABLED: Local MIA not following instructions properly
        # Skip local and go straight to remote MIA backend which works correctly
        skip_local = True  # Set to False to re-enable local MIA
        
        if not skip_local:
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
        
        # Try remote MIA backend (this works correctly)
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

def format_menu_for_context(menu_items, query):
    """
    Simple context builder - let the AI figure out what's relevant
    """
    if not menu_items:
        return ""
    
    query_lower = query.lower()
    
    # For general menu requests, show a sample
    if any(word in query_lower for word in ['menu', 'offer', 'serve']):
        categories = {}
        for item in menu_items[:30]:
            cat = item.get('subcategory', 'main')
            if cat not in categories:
                categories[cat] = []
            name = item.get('name') or item.get('dish', '')
            if name:
                categories[cat].append(name)
        
        lines = []
        for cat, items in categories.items():
            if items:
                lines.append(f"{cat.title()}: {', '.join(items[:5])}")
        return "\n".join(lines)
    
    # For specific queries, find relevant items
    found_items = []
    
    # Get meaningful words from query (skip common words)
    query_words = [w for w in query_lower.split() if len(w) > 2 and w not in ['what', 'have', 'you', 'the', 'are', 'your', 'our', 'any', 'some', 'can', 'get']]
    
    if query_words:  # Only search if there are meaningful words
        for item in menu_items:
            name = item.get('name') or item.get('dish', '')
            if not name:
                continue
                
            # Check if any query word matches the item
            item_text = f"{name} {item.get('description', '')} {' '.join(item.get('ingredients', []))}".lower()
            
            if any(word in item_text for word in query_words):
                found_items.append({
                    'name': name,
                    'price': item.get('price', ''),
                    'category': item.get('subcategory', 'main')
                })
    
    # Format found items
    if found_items:
        by_category = {}
        for item in found_items[:30]:  # Reasonable limit
            cat = item['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f"{item['name']} ({item['price']})")
        
        lines = []
        for cat, items in by_category.items():
            lines.append(f"{cat.title()}: {', '.join(items)}")
        return "\n".join(lines)
    
    return ""  # No relevant context

def mia_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Handle chat requests using MIA backend"""
    
    logger.info(f"MIA CHAT SERVICE - Restaurant: {req.restaurant_id}, Client: {req.client_id}")
    logger.info(f"Query: '{req.message}'")
    
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
        
        # Add menu context if relevant
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
        answer = get_mia_response_direct(full_prompt, max_tokens=250)
        
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

# Helper functions
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