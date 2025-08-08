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
from functools import lru_cache
import hashlib

logger = logging.getLogger(__name__)

# Global cache for categorized menus
_menu_cache = {}

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

def categorize_menu_items(menu_items):
    """Categorize menu items - this is cached for performance."""
    categories = {}
    dietary_items = {
        'vegetarian': [],
        'vegan': [],
        'gluten_free': [],
        'dairy_free': []
    }
    
    # Single pass through menu items for categorization
    for item in menu_items:
        name = item.get('name') or item.get('dish') or item.get('title', '')
        if not name:
            continue
            
        # Add to category
        category = item.get('subcategory', 'main')
        if category not in categories:
            categories[category] = []
        categories[category].append(item)
        
        # Check dietary restrictions
        ingredients = item.get('ingredients', [])
        allergens = item.get('allergens', [])
        ingredients_lower = [ing.lower() for ing in ingredients]
        
        # Vegetarian check (no meat)
        meat_keywords = ['beef', 'pork', 'chicken', 'duck', 'lamb', 'veal', 'bacon', 'guanciale', 'pancetta']
        if not any(meat in ingredients_lower for meat in meat_keywords):
            if not any(seafood in ingredients_lower for seafood in ['fish', 'shrimp', 'lobster', 'scallop', 'calamari', 'oyster']):
                dietary_items['vegetarian'].append(item)
                # Vegan check (no animal products)
                if not any(dairy in ingredients_lower for dairy in ['cheese', 'cream', 'butter', 'milk', 'egg', 'mozzarella', 'parmesan']):
                    dietary_items['vegan'].append(item)
        
        # Gluten-free check
        if 'gluten' not in allergens:
            dietary_items['gluten_free'].append(item)
        
        # Dairy-free check
        if 'dairy' not in allergens:
            dietary_items['dairy_free'].append(item)
    
    return categories, dietary_items

def format_menu_for_context(menu_items, query, restaurant_id=None):
    """Format menu items for context - optimized for performance and relevance."""
    if not menu_items:
        return "Menu data unavailable."
    
    query_lower = query.lower()
    
    # Try to get cached categorization for performance
    cache_key = None
    if restaurant_id:
        # Create a hash of menu items for cache invalidation
        menu_str = str([(item.get('name', ''), item.get('ingredients', [])) for item in menu_items[:5]])
        menu_hash = hashlib.md5(menu_str.encode()).hexdigest()[:8]
        cache_key = f"{restaurant_id}_{menu_hash}"
        
        if cache_key in _menu_cache:
            categories, dietary_items = _menu_cache[cache_key]
        else:
            categories, dietary_items = categorize_menu_items(menu_items)
            _menu_cache[cache_key] = (categories, dietary_items)
            # Keep cache size reasonable
            if len(_menu_cache) > 100:
                _menu_cache.clear()
    else:
        categories, dietary_items = categorize_menu_items(menu_items)
    
    # Build context based on query type
    context_parts = []
    
    # Check for dietary queries
    if any(diet in query_lower for diet in ['vegetarian', 'vegan']):
        veg_items = dietary_items['vegetarian'][:8]  # Limit for performance
        if veg_items:
            veg_list = []
            for item in veg_items:
                name = item.get('name') or item.get('dish', '')
                desc = item.get('description', '')[:50]
                veg_list.append(f"{name} - {desc}")
            context_parts.append("Vegetarian options:\n" + "\n".join(veg_list))
    
    elif 'gluten' in query_lower:
        gf_items = dietary_items['gluten_free'][:8]
        if gf_items:
            gf_list = [item.get('name') or item.get('dish', '') for item in gf_items]
            context_parts.append("Gluten-free options: " + ", ".join(gf_list))
    
    # Check for category queries
    elif any(cat in query_lower for cat in ['starter', 'appetizer', 'dessert', 'main']):
        for cat_name, cat_items in categories.items():
            if cat_name.lower() in query_lower:
                items_info = []
                for item in cat_items[:6]:  # Limit items per category
                    name = item.get('name') or item.get('dish', '')
                    price = item.get('price', '')
                    items_info.append(f"{name} ({price})")
                context_parts.append(f"{cat_name.title()} dishes: " + ", ".join(items_info))
    
    # Check for general menu queries
    elif any(word in query_lower for word in ['menu', 'serve', 'offer', 'have', 'dishes']):
        # Provide menu overview
        overview = []
        for cat_name, cat_items in categories.items():
            sample_items = [item.get('name') or item.get('dish', '') for item in cat_items[:3]]
            overview.append(f"{cat_name.title()} ({len(cat_items)} items): {', '.join(sample_items)}")
        context_parts.append("Menu Overview:\n" + "\n".join(overview))
    
    # Specific item search
    else:
        # Look for specific items mentioned in query
        relevant_items = []
        query_words = [w for w in query_lower.split() if len(w) > 3]
        
        for item in menu_items[:30]:  # Limit search for performance
            name = item.get('name') or item.get('dish', '')
            name_lower = name.lower()
            ingredients = item.get('ingredients', [])
            
            # Check if item is relevant
            if any(word in name_lower for word in query_words) or \
               any(word in ing.lower() for ing in ingredients for word in query_words):
                price = item.get('price', '')
                ing_list = ', '.join(ingredients[:4])
                allergens = item.get('allergens', [])
                allergen_info = f" (Allergens: {', '.join(allergens)})" if allergens and allergens[0] != 'none' else ""
                relevant_items.append(f"{name} ({price}): {ing_list}{allergen_info}")
        
        if relevant_items:
            context_parts.append("Relevant items:\n" + "\n".join(relevant_items[:5]))
        else:
            # If no specific matches, provide popular items from different categories
            popular = []
            for cat_name, cat_items in categories.items():
                if cat_items:
                    item = cat_items[0]
                    name = item.get('name') or item.get('dish', '')
                    popular.append(f"{name} ({cat_name})")
            if popular:
                context_parts.append("Popular dishes: " + ", ".join(popular[:6]))
    
    return "\n".join(context_parts) if context_parts else "Please ask about specific dishes, categories, or dietary preferences."

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
    
    # Handle different data structures efficiently
    menu_items = []
    opening_hours = None
    contact_info = None
    
    # First try the database JSON structure
    if restaurant.data:
        data = restaurant.data
        menu_items = data.get("menu", [])
        opening_hours = data.get("opening_hours")
        contact_info = data.get("contact_info")
    
    # If no menu in data field, try to construct from restaurant model
    if not menu_items and hasattr(restaurant, '__dict__'):
        # Check if restaurant has these as direct attributes (from API response)
        restaurant_dict = restaurant.__dict__
        menu_items = restaurant_dict.get('menu', [])
        if not opening_hours:
            opening_hours = restaurant_dict.get('opening_hours')
        if not contact_info:
            contact_info = restaurant_dict.get('contact_info')
    
    # Apply menu fallbacks if we have items
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
        
        if needs_hours and opening_hours:
            if isinstance(opening_hours, dict):
                hours_text = "\n".join([f"{day}: {hours}" for day, hours in opening_hours.items()])
                context_parts.append(f"Opening Hours:\n{hours_text}")
            else:
                context_parts.append(f"Hours: {opening_hours}")
            
        if needs_contact and contact_info:
            context_parts.append(f"Contact: {contact_info}")
        
        # Add menu context if relevant
        menu_context = format_menu_for_context(validated_menu, req.message, req.restaurant_id)
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