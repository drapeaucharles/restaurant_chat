"""
DB Query MIA Chat Service - AI queries database only when needed
No menu data sent upfront, AI requests what it needs
"""
import requests
import json
import re
from typing import Dict, Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime
import models
from schemas.chat import ChatRequest, ChatResponse
import os
import logging
from services.mia_chat_service_hybrid import get_mia_response_hybrid
from services.customer_memory_service import CustomerMemoryService
try:
    from services.mia_fast_polling import get_mia_response_fast
    USE_FAST_POLLING = True
except ImportError:
    USE_FAST_POLLING = False
    logger.warning("Fast polling not available, using standard MIA polling")

logger = logging.getLogger(__name__)

def get_menu_categories(db: Session, restaurant_id: str) -> List[str]:
    """Get just the menu categories (using subcategories for bella_vista)"""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant or not restaurant.data:
        return []
    
    menu_items = restaurant.data.get('menu', [])
    categories = set()
    for item in menu_items:
        # For bella_vista, subcategory is the actual category
        cat = item.get('subcategory') or item.get('category', 'Other')
        categories.add(cat)
    
    return sorted(list(categories))

def get_dishes_in_category(db: Session, restaurant_id: str, category: str) -> List[Dict]:
    """Get dishes in a specific category"""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant or not restaurant.data:
        return []
    
    menu_items = restaurant.data.get('menu', [])
    dishes = []
    for item in menu_items:
        # Check both category and subcategory
        item_cat = item.get('subcategory') or item.get('category', '')
        if item_cat.lower() == category.lower():
            dishes.append({
                'name': item.get('dish') or item.get('name', ''),
                'price': item.get('price', '')
            })
    
    return dishes

def search_dish_by_name(db: Session, restaurant_id: str, dish_name: str) -> Optional[Dict]:
    """Search for a specific dish by name"""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant or not restaurant.data:
        return None
    
    menu_items = restaurant.data.get('menu', [])
    dish_name_lower = dish_name.lower()
    
    # First try exact match
    for item in menu_items:
        name = (item.get('dish') or item.get('name', '')).lower()
        if dish_name_lower == name:
            return item
    
    # Then try partial match
    for item in menu_items:
        name = (item.get('dish') or item.get('name', '')).lower()
        if dish_name_lower in name or name in dish_name_lower:
            return item
    
    # Finally try word-by-word match
    dish_words = dish_name_lower.split()
    for item in menu_items:
        name = (item.get('dish') or item.get('name', '')).lower()
        if all(word in name for word in dish_words):
            return item
    
    return None

def search_dishes_by_ingredient(db: Session, restaurant_id: str, ingredient: str) -> List[Dict]:
    """Search for dishes containing a specific ingredient"""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant or not restaurant.data:
        return []
    
    menu_items = restaurant.data.get('menu', [])
    ingredient_lower = ingredient.lower()
    matching_dishes = []
    
    for item in menu_items:
        # Check in dish name
        dish_name = (item.get('dish') or item.get('name', '')).lower()
        if ingredient_lower in dish_name:
            matching_dishes.append(item)
            continue
            
        # Check in ingredients list
        ingredients = item.get('ingredients', [])
        if any(ingredient_lower in ing.lower() for ing in ingredients):
            matching_dishes.append(item)
            continue
            
        # Check in description
        description = item.get('description', '').lower()
        if ingredient_lower in description:
            matching_dishes.append(item)
    
    return matching_dishes

def get_popular_dishes(db: Session, restaurant_id: str) -> List[Dict]:
    """Get a selection of popular dishes across categories"""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant or not restaurant.data:
        return []
    
    menu_items = restaurant.data.get('menu', [])
    
    # Get 2 from each category
    suggestions = []
    categories = ['starter', 'main', 'dessert']
    
    for category in categories:
        category_dishes = [item for item in menu_items 
                         if (item.get('subcategory') or item.get('category', '')).lower() == category]
        
        # For bella_vista, we'll suggest some specific popular items
        if category == 'starter' and category_dishes:
            # Look for specific dishes or just take first 2
            for dish in category_dishes:
                if any(word in dish.get('dish', '').lower() 
                      for word in ['bruschetta', 'calamari', 'caprese']):
                    suggestions.append(dish)
                    if len([s for s in suggestions if s.get('subcategory') == 'starter']) >= 2:
                        break
        
        elif category == 'main' and category_dishes:
            for dish in category_dishes:
                if any(word in dish.get('dish', '').lower() 
                      for word in ['lobster', 'risotto', 'lamb']):
                    suggestions.append(dish)
                    if len([s for s in suggestions if s.get('subcategory') == 'main']) >= 2:
                        break
        
        elif category == 'dessert' and category_dishes:
            suggestions.extend(category_dishes[:1])  # Just one dessert
    
    # If we didn't get enough specific dishes, add some from each category
    for category in categories:
        current_count = len([s for s in suggestions 
                           if (s.get('subcategory') or s.get('category', '')).lower() == category])
        if current_count < 1:
            category_dishes = [item for item in menu_items 
                             if (item.get('subcategory') or item.get('category', '')).lower() == category]
            suggestions.extend(category_dishes[:1-current_count])
    
    return suggestions

def parse_ai_request(message: str) -> Tuple[str, Optional[str]]:
    """Parse what the AI is asking for"""
    message_lower = message.lower()
    
    # Check if asking for suggestions/recommendations
    if any(word in message_lower for word in ['suggest', 'recommend', 'recommendation', 'popular', 'best', 'favorite']):
        return 'suggestions', None
    
    # Check if asking for categories
    if any(word in message_lower for word in ['categories', 'types', 'sections', 'what kind']):
        return 'categories', None
    
    # Check if asking about specific category
    category_keywords = {
        'starter': ['appetizer', 'starter', 'first course', 'appetizers', 'starters'],
        'main': ['main', 'entree', 'main course', 'dinner', 'mains', 'entrees'],
        'dessert': ['dessert', 'sweet', 'cake', 'ice cream', 'desserts'],
        'drinks': ['drink', 'beverage', 'wine', 'beer', 'cocktail', 'drinks']
    }
    
    for category, keywords in category_keywords.items():
        if any(keyword in message_lower for keyword in keywords):
            return 'category_dishes', category
    
    # Check if asking about specific dish
    if any(phrase in message_lower for phrase in ['tell me about', 'describe', 'what is', "what's in", 'ingredients', 'price of']):
        # Extract dish name after these phrases
        for phrase in ['tell me about', 'describe', 'what is', "what's in", 'price of']:
            if phrase in message_lower:
                potential_dish = message_lower.split(phrase)[-1].strip()
                # Clean up common endings
                potential_dish = potential_dish.rstrip('?.,!').strip()
                if potential_dish:
                    return 'dish_details', potential_dish
    
    # Check for ingredient preferences
    ingredient_patterns = [
        r'i (?:like|love|want|prefer|enjoy) (\w+)',
        r'anything with (\w+)',
        r'something with (\w+)',
        r'dishes? with (\w+)',
        r'dishes? (?:containing|that have|that contain) (\w+)',
        r'(\w+) dishes?',
        r'do you have.*with (\w+)',
        r'something (\w+)',  # Catches "something vegetarian", "something spicy"
        r'anything (\w+)',   # Catches "anything vegan", "anything gluten-free"
        r'any other (\w+)',  # Catches "any other pasta"
        r'other (\w+) dishes?',  # Catches "other pasta dishes"
        r'do you have (\w+)',  # Catches "do you have pasta"
        r'show me (\w+)'  # Catches "show me pasta"
    ]
    
    import re
    for pattern in ingredient_patterns:
        match = re.search(pattern, message_lower)
        if match:
            ingredient = match.group(1)
            # Filter out category words
            if ingredient not in ['something', 'anything', 'food', 'dishes', 'dish', 'items', 'options']:
                return 'ingredient_search', ingredient
    
    return 'general', None

def mia_chat_service_db_query(req: ChatRequest, db: Session) -> ChatResponse:
    """DB Query chat service - AI queries database as needed"""
    
    try:
        logger.info(f"DB QUERY SERVICE - Request: {req.message[:50]}...")
        
        # Skip AI for restaurant staff messages
        if req.sender_type == 'restaurant':
            return ChatResponse(answer="")
        
        # Get basic restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
        
        data = restaurant.data or {}
        business_name = data.get('restaurant_name', req.restaurant_id)
        
        # Customer profile handling
        extracted_info = CustomerMemoryService.extract_customer_info(req.message)
        if extracted_info:
            profile = CustomerMemoryService.update_customer_profile(
                db, req.client_id, req.restaurant_id, extracted_info
            )
        else:
            client_id_str = str(req.client_id)
            profile = db.query(models.CustomerProfile).filter(
                models.CustomerProfile.client_id == client_id_str,
                models.CustomerProfile.restaurant_id == req.restaurant_id
            ).first()
        
        customer_context = CustomerMemoryService.get_customer_context(profile)
        
        # Parse what the user is asking for
        request_type, request_detail = parse_ai_request(req.message)
        
        # Build context based on request
        menu_context = ""
        if request_type == 'suggestions':
            dishes = get_popular_dishes(db, req.restaurant_id)
            if dishes:
                menu_context = "Today's recommendations:\n"
                for d in dishes:
                    name = d.get('dish') or d.get('name', '')
                    price = d.get('price', '')
                    category = d.get('subcategory', '')
                    desc = d.get('description', '')[:80] + '...' if len(d.get('description', '')) > 80 else d.get('description', '')
                    menu_context += f"\n{category.title()}:\n- {name} ({price})\n  {desc}\n"
        
        elif request_type == 'categories':
            categories = get_menu_categories(db, req.restaurant_id)
            menu_context = f"Menu categories available: {', '.join(categories)}"
        
        elif request_type == 'category_dishes':
            dishes = get_dishes_in_category(db, req.restaurant_id, request_detail)
            if dishes:
                dish_list = [f"{d['name']} ({d['price']})" for d in dishes]
                menu_context = f"{request_detail.title()} dishes: {', '.join(dish_list)}"
            else:
                menu_context = f"No {request_detail} items found."
        
        elif request_type == 'dish_details':
            dish = search_dish_by_name(db, req.restaurant_id, request_detail)
            if dish:
                details = []
                details.append(f"Dish: {dish.get('dish') or dish.get('name', '')}")
                if dish.get('description'):
                    details.append(f"Description: {dish['description']}")
                if dish.get('ingredients'):
                    details.append(f"Ingredients: {', '.join(dish['ingredients'])}")
                if dish.get('allergens'):
                    details.append(f"Allergens: {', '.join(dish['allergens'])}")
                if dish.get('price'):
                    details.append(f"Price: {dish['price']}")
                menu_context = '\n'.join(details)
            else:
                menu_context = f"I couldn't find a dish matching '{request_detail}'. Would you like me to show you our menu categories?"
        
        elif request_type == 'ingredient_search':
            dishes = search_dishes_by_ingredient(db, req.restaurant_id, request_detail)
            if dishes:
                dish_summaries = []
                for d in dishes[:5]:  # Limit to 5 dishes
                    name = d.get('dish') or d.get('name', '')
                    price = d.get('price', '')
                    category = d.get('subcategory', '')
                    dish_summaries.append(f"{name} ({category}) - {price}")
                menu_context = f"Dishes with {request_detail}:\n" + '\n'.join(dish_summaries)
                if len(dishes) > 5:
                    menu_context += f"\n...and {len(dishes) - 5} more dishes with {request_detail}"
            else:
                menu_context = f"I couldn't find any dishes with {request_detail}."
        
        # System prompt that teaches AI how to ask for data
        system_prompt = f"""You are Maria, a friendly server at {business_name}.

You have access to the restaurant's database. When customers ask about the menu:
- If they ask what's available, mention you can show them the menu categories
- If they ask about a category (appetizers, mains, etc), I'll provide those dishes
- If they ask about a specific dish, I'll give you full details
- If they mention liking an ingredient or wanting something with specific ingredients, I'll show you matching dishes
- Always be helpful and guide them through the menu

Current context:
{menu_context}

Keep responses natural and conversational. If you don't have the info they need, suggest what you can show them."""

        # Get recent chat history
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
        
        chat_history = []
        for msg in reversed(recent_messages[1:]):
            if msg.sender_type == "client":
                chat_history.append(f"Customer: {msg.message}")
            elif msg.sender_type == "ai":
                chat_history.append(f"Assistant: {msg.message}")
        
        history_text = "\n".join(chat_history[-6:]) if chat_history else ""
        
        # Build prompt
        full_prompt = f"""{system_prompt}

Customer Profile:
{customer_context}

Previous conversation:
{history_text}

Customer: {req.message}
Assistant:"""
        
        logger.info(f"DB Query using request type: {request_type}, detail: {request_detail}")
        
        # Get AI response
        params = {
            "temperature": 0.7,
            "max_tokens": 300 if request_type != 'dish_details' else 500
        }
        
        # Log timing
        import time
        start_time = time.time()
        
        # Use fast polling if available
        if USE_FAST_POLLING:
            logger.info("Using fast polling for MIA")
            answer = get_mia_response_fast(full_prompt, params)
        else:
            answer = get_mia_response_hybrid(full_prompt, params)
            
        elapsed = time.time() - start_time
        logger.info(f"MIA response time: {elapsed:.1f} seconds")
        
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
        logger.error(f"Error in db_query service: {str(e)}", exc_info=True)
        try:
            db.rollback()
        except:
            pass
        return ChatResponse(answer="I apologize, but I'm having trouble accessing the menu information. Please try again.")