"""
MIA Chat Service - Fixed version for direct API calls
Uses MIA backend as a direct service instead of distributed network
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
MIA_LOCAL_URL = os.getenv("MIA_LOCAL_URL", "http://localhost:8001")  # Different port for local

# System prompt adapted for MIA
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
    """
    Get response from MIA using direct API endpoint
    
    Args:
        prompt: The formatted prompt to send to MIA
        max_tokens: Maximum tokens to generate
        
    Returns:
        Generated response text
    """
    try:
        # First try local MIA instance
        try:
            response = requests.post(
                f"{MIA_LOCAL_URL}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "restaurant_mode": True  # Special flag for restaurant requests
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "I'm having trouble understanding. Could you please rephrase?")
        except:
            logger.info("Local MIA not available, trying remote")
        
        # Try remote MIA backend with direct generation endpoint
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",  # Direct generation endpoint
            json={
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "source": "restaurant"  # Identify source
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
            
            # Fallback response
            return "I apologize, but I'm having technical difficulties. Please try again in a moment or ask our staff for assistance."
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "I'm taking a bit longer to respond. Please try again."
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}")
        return "I'm experiencing technical difficulties. Please try again or ask our staff for help."

def fetch_recent_chat_history(db: Session, client_id: str, restaurant_id: str):
    """
    Fetch recent chat history for context.
    
    Returns messages from the last 60 minutes, maximum of 20 messages,
    sorted chronologically (oldest to newest).
    """
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

def filter_essential_messages(messages):
    """
    Filter out non-essential messages to reduce token usage.
    """
    non_essential_patterns = [
        r'^(ok|okay|thanks|thank you|yes|no|yeah|yep|nope|sure|alright|got it|understood|perfect|great|good|nice|cool|awesome)\.?$',
        r'^(hi|hello|hey|bye|goodbye|see you|later)\.?$',
        r'^👍|😊|😄|🙏|✅|👌$',
        r'^\.$',
        r'^!+$',
    ]
    
    essential_keywords = [
        'what', 'how', 'when', 'where', 'why', 'which', 'who',
        'allerg', 'gluten', 'vegan', 'vegetarian', 'dairy', 'nut', 'ingredient',
        'spicy', 'mild', 'recommend', 'suggest', 'best', 'popular', 'favorite',
        'price', 'cost', 'expensive', 'cheap', 'budget',
        'don\'t like', 'avoid', 'without', 'no ', 'free from',
        'show', 'filter', 'only', 'menu', 'options', 'dishes',
        '?'
    ]
    
    filtered_messages = []
    
    for msg in messages:
        message_lower = msg.message.lower().strip()
        
        if msg.sender_type == 'ai':
            filtered_messages.append(msg)
            continue
            
        is_non_essential = any(re.match(pattern, message_lower, re.IGNORECASE) for pattern in non_essential_patterns)
        contains_essential = any(keyword in message_lower for keyword in essential_keywords)
        
        if not is_non_essential or contains_essential:
            filtered_messages.append(msg)
    
    return filtered_messages

def format_chat_history_for_prompt(chat_history):
    """
    Format chat history messages for MIA prompt.
    """
    formatted_messages = []
    
    for msg in chat_history:
        if msg.sender_type == 'client':
            formatted_messages.append(f"Customer: {msg.message}")
        elif msg.sender_type == 'ai':
            formatted_messages.append(f"Assistant: {msg.message}")
    
    return "\n".join(formatted_messages)

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
    """Format only relevant menu items based on the query."""
    if not menu_items:
        return "Menu data unavailable."
    
    query_lower = query.lower()
    relevant_items = []
    all_item_names = []
    
    for item in menu_items:
        name = item.get('name') or item.get('dish') or item.get('title', '')
        if name:
            all_item_names.append(name)
    
    for item in menu_items:
        try:
            name = item.get('name') or item.get('dish') or item.get('title', '')
            if not name:
                continue
                
            name_lower = name.lower()
            ingredients = item.get('ingredients', [])
            
            is_relevant = (
                name_lower in query_lower or
                any(word in name_lower for word in query_lower.split() if len(word) > 3) or
                any(ing.lower() in query_lower for ing in ingredients if len(ing) > 3)
            )
            
            if is_relevant:
                allergens = item.get('allergens', [])
                item_info = f"[EXACT: {name}]: {', '.join(ingredients[:5])}"
                if allergens and allergens[0] != 'none':
                    item_info += f" (Allergens: {', '.join(allergens)})"
                relevant_items.append(item_info)
                
        except Exception as e:
            continue
    
    context_parts = []
    
    if relevant_items:
        context_parts.append("Relevant menu items: " + "; ".join(relevant_items[:5]))
    
    if any(word in query_lower for word in ['recommend', 'suggest', 'good', 'best', 'popular', 'try']):
        sample_names = all_item_names[:10] if len(all_item_names) > 10 else all_item_names
        context_parts.append(f"VALIDATION: Only these items exist: {', '.join(sample_names)}...")
    
    return "\n".join(context_parts) if context_parts else ""

def mia_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Handle chat requests using MIA backend."""
    
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
    
    # Check recent staff messages
    recent_cutoff = datetime.utcnow() - timedelta(seconds=10)
    recent_staff_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == req.client_id,
        models.ChatMessage.restaurant_id == req.restaurant_id,
        models.ChatMessage.sender_type == 'restaurant',
        models.ChatMessage.timestamp >= recent_cutoff
    ).order_by(models.ChatMessage.timestamp.desc()).all()
    
    is_staff_message = any(
        staff_msg.message.strip() == req.message.strip() 
        for staff_msg in recent_staff_messages
    )
    
    if is_staff_message:
        logger.info("Blocking AI response - matches recent staff message")
        return ChatResponse(answer="")
    
    # Check cache
    cached_response = response_cache.get(req.restaurant_id, req.message)
    if cached_response:
        logger.info("Using cached response")
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=cached_response
        )
        db.add(new_message)
        db.commit()
        return ChatResponse(answer=cached_response)
    
    # Check AI enabled state
    client = get_or_create_client(db, req.client_id, req.restaurant_id)
    ai_enabled_state = True
    if client.preferences:
        ai_enabled_state = client.preferences.get("ai_enabled", True)
    
    if not ai_enabled_state:
        logger.info("AI is disabled for this conversation")
        return ChatResponse(answer="")
    
    data = restaurant.data or {}
    
    try:
        # Prepare context
        menu_items = data.get("menu", [])
        if menu_items:
            try:
                menu_items = apply_menu_fallbacks(menu_items)
            except Exception as e:
                logger.warning(f"Error applying menu fallbacks: {e}")
        
        validated_menu = []
        for item in menu_items:
            if isinstance(item, dict):
                validated_item = {
                    'name': item.get('name') or item.get('dish', 'Unknown Dish'),
                    'description': item.get('description', 'No description available'),
                    'ingredients': item.get('ingredients', []),
                    'allergens': item.get('allergens', []),
                    'price': item.get('price', 'Price not available')
                }
                validated_menu.append(validated_item)
        
        # Build context
        query_lower = req.message.lower()
        context_parts = [system_prompt]
        
        # Add restaurant context
        context_parts.append(f"\nRestaurant: {restaurant.restaurant_id}")
        context_parts.append(f"Customer asks: '{req.message}'")
        context_parts.append("(Customer is viewing the complete menu on their screen)")
        
        # Add specific context based on query
        needs_hours = any(term in query_lower for term in ['open', 'close', 'hour', 'when', 'time'])
        needs_contact = any(term in query_lower for term in ['phone', 'call', 'contact', 'email', 'address'])
        
        if needs_hours:
            context_parts.append(f"Hours: {data.get('opening_hours', 'Check with staff')}")
            
        if needs_contact:
            context_parts.append(f"Contact: {data.get('contact_info', 'Ask staff')}")
        
        # Add menu context if relevant
        menu_context = format_menu_for_context(validated_menu, req.message)
        if menu_context:
            context_parts.append(menu_context)
        
        # Add recent chat history
        recent_history = fetch_recent_chat_history(db, req.client_id, req.restaurant_id)
        if recent_history:
            filtered_history = filter_essential_messages(recent_history[-6:])
            if filtered_history:
                context_parts.append("\nRecent conversation:")
                context_parts.append(format_chat_history_for_prompt(filtered_history))
        
        # Final prompt
        full_prompt = "\n".join(context_parts)
        full_prompt += f"\n\nCustomer: {req.message}\nAssistant:"
        
        # Get response from MIA using direct API
        answer = get_mia_response_direct(full_prompt, max_tokens=150)
        
        # Cache common queries
        query_type = response_cache.get_query_type(req.message)
        if query_type in ['hours', 'location', 'contact', 'wifi', 'parking', 'payment']:
            response_cache.set(req.restaurant_id, req.message, answer)
        
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