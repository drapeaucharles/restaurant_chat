"""
MIA Chat Service with Internal Tool Flow V5 - 2-PHASE SYSTEM
Optimized version with only 2 AI calls instead of 3
"""
import os
import requests
import json
import logging
import time
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def create_menu_summary(menu_items: List[Dict]) -> str:
    """Create a compressed menu with all items but no descriptions"""
    if not menu_items:
        return "No menu items available."
    
    # Group by category for better organization
    categories = {}
    for item in menu_items:
        cat = item.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        
        name = item.get('dish') or item.get('name', '')
        price = item.get('price', '')
        allergens = item.get('allergens', [])
        
        # Compressed format without description
        if allergens:
            categories[cat].append(f"{name} {price} [{', '.join(allergens)}]")
        else:
            categories[cat].append(f"{name} {price}")
    
    # Build compressed menu
    summary = "FULL MENU (compressed):\n"
    for cat, items in sorted(categories.items()):
        summary += f"\n{cat}:\n"
        for item in items:
            summary += f"- {item}\n"
    
    return summary

def get_available_categories(menu_items: List[Dict]) -> Dict[str, List[str]]:
    """Extract unique categories from menu organized by type"""
    meal_times = set()
    course_types = set()
    food_categories = set()
    
    for item in menu_items:
        if item.get('category'):
            meal_times.add(item.get('category'))
        if item.get('subcategory'):
            course_types.add(item.get('subcategory'))
        
        # Handle both single category and array of categories
        if item.get('restaurant_categories'):
            # New array format
            for cat in item.get('restaurant_categories', []):
                food_categories.add(cat)
        elif item.get('restaurant_category'):
            # Old single category format
            food_categories.add(item.get('restaurant_category'))
    
    return {
        'meal_times': sorted(list(meal_times)),
        'course_types': sorted(list(course_types)),
        'food_categories': sorted(list(food_categories))
    }

def get_available_dish_names(menu_items: List[Dict]) -> List[str]:
    """Extract all dish names from menu"""
    names = []
    for item in menu_items:
        name = item.get('dish') or item.get('name', '')
        if name:
            names.append(name)
    return names

def get_customer_profile(db: Session, client_id: str, restaurant_id: str) -> Optional[Any]:
    """Get or create customer profile with allergies and preferences"""
    try:
        # Get existing profile
        client_id_str = str(client_id)
        profile = db.query(models.CustomerProfile).filter(
            models.CustomerProfile.client_id == client_id_str,
            models.CustomerProfile.restaurant_id == restaurant_id
        ).first()
        
        if not profile:
            # Create new profile
            profile = models.CustomerProfile(
                client_id=client_id_str,
                restaurant_id=restaurant_id,
                allergies=[],
                dietary_restrictions=[]
            )
            db.add(profile)
            db.commit()
            
        return profile
    except Exception as e:
        logger.warning(f"Could not load customer profile: {e}")
        return None

def get_chat_history(db: Session, client_id: str, restaurant_id: str, limit: int = 5) -> List[Dict]:
    """Get recent chat history for context - resets after 30 minutes of inactivity"""
    from datetime import datetime, timedelta, timezone
    
    try:
        # First check the most recent message timestamp
        latest_message = db.query(models.ChatMessage).filter(
            models.ChatMessage.client_id == client_id,
            models.ChatMessage.restaurant_id == restaurant_id
        ).order_by(models.ChatMessage.timestamp.desc()).first()
        
        # If no messages or last message is older than 30 minutes, return empty history
        if latest_message:
            # Use timezone-aware UTC datetime to match database timestamps
            time_since_last = datetime.now(timezone.utc) - latest_message.timestamp
            if time_since_last > timedelta(minutes=30):
                logger.info(f"Conversation timeout - last message was {time_since_last.seconds // 60} minutes ago. Starting fresh.")
                return []
        
        # Get messages from the last 30 minutes only
        cutoff_time = datetime.now(timezone.utc) - timedelta(minutes=30)
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.client_id == client_id,
            models.ChatMessage.restaurant_id == restaurant_id,
            models.ChatMessage.timestamp >= cutoff_time
        ).order_by(models.ChatMessage.timestamp.desc()).limit(limit * 2).all()
        
        history = []
        for msg in reversed(messages):
            history.append({
                "role": "user" if msg.sender_type in ["customer", "client"] else "assistant",
                "message": msg.message
            })
        
        return history[-limit * 2:]  # Return only the requested number of messages
    except Exception as e:
        logger.warning(f"Could not load chat history: {e}")
        return []

def get_context_type(customer_profile: Any, message: str) -> Tuple[str, Dict]:
    """Determine context type based on customer profile and message"""
    context_data = {}
    message_lower = message.lower()
    
    # Check for allergy correction/removal patterns
    removal_patterns = [
        'not allergic', 'no allergy', "don't have allergy", 
        'can eat', 'was a joke', 'made a mistake',
        'for my friend', 'for someone else', "isn't for me",
        'actually i can', 'show me with'
    ]
    
    if any(pattern in message_lower for pattern in removal_patterns):
        return "allergy_correction", context_data
    
    # Check if customer has allergies
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary_restrictions = getattr(customer_profile, 'dietary_restrictions', []) or []
        all_restrictions = allergies + dietary_restrictions
        
        if all_restrictions:
            context_data = {
                'allergens': allergies,
                'dietary_preferences': dietary_restrictions,
                'all_restrictions': all_restrictions,
                'strict_mode': True
            }
            if any(allergen.lower() in message_lower and 'with' in message_lower for allergen in allergies):
                return "allergy_correction", context_data
            return "allergen_safety", context_data
    
    # Check message for allergy/dietary mentions
    allergen_keywords = ['allerg', 'intolerant', 'can\'t eat', 'avoid', 'free from']
    dietary_keywords = ['vegan', 'vegetarian', 'gluten', 'dairy', 'nut']
    
    if any(keyword in message_lower for keyword in allergen_keywords + dietary_keywords):
        return "allergen_query", context_data
    
    return "general", context_data

def build_phase1_prompt(message: str, customer_profile: Any, chat_history: List[Dict], 
                       menu_items: List[Dict], restaurant_name: str) -> str:
    """Build Phase 1 prompt with restaurant context for tool AND parameter selection"""
    
    # Get available data
    categories = get_available_categories(menu_items)
    dish_names = get_available_dish_names(menu_items)
    
    prompt = f"""You are a tool selector for {restaurant_name}. Analyze the conversation and select tools WITH parameters.

"""
    
    # Add chat history
    if chat_history and len(chat_history) > 0:
        prompt += "CONVERSATION HISTORY:\n"
        for msg in chat_history[:-1]:
            role = "Customer" if msg["role"] == "user" else "You"
            prompt += f"{role}: {msg['message']}\n"
        prompt += "\n"
    
    prompt += f"""CURRENT MESSAGE: "{message}"

"""
    
    # Add customer context
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary = getattr(customer_profile, 'dietary_restrictions', []) or []
        
        if allergies or dietary:
            prompt += f"""CUSTOMER INFO:
- Allergies: {', '.join(allergies) if allergies else 'None'}
- Dietary: {', '.join(dietary) if dietary else 'None'}

"""
    
    # Add restaurant context
    prompt += f"""RESTAURANT CONTEXT:
- Meal times: {', '.join(categories['meal_times'])} (when dishes are served)
- Course types: {', '.join(categories['course_types'])} (starter, main, dessert)
- Food categories: {', '.join(categories['food_categories'])} (type of food)
- All dishes in menu: {', '.join(dish_names)}

AVAILABLE TOOLS:
1. get_dish_details - Get info about a SPECIFIC dish
   Parameters: dish_name (can be partial like "carbonara" or have typos like "lasagni" - the tool will fuzzy match)
   
2. search_by_meal_time - Search dishes by when they're served
   Parameters: meal_time (from available: {', '.join(categories['meal_times'])})
   
3. search_by_course_type - Search dishes by course
   Parameters: course_type (from available: {', '.join(categories['course_types'])})
   
4. search_by_food_type - Search dishes by food category
   Parameters: food_type (from available: {', '.join(categories['food_categories'])})
   Note: Items can belong to multiple categories (e.g., Salmon is both "Fish" and "Seafood")
   
5. search_menu_by_ingredient - Search dishes containing ingredient
   Parameters: ingredient (any ingredient name)
   
6. filter_vegetarian/vegan/gluten_free/nut_free/dairy_free/shellfish_free - Filter safe dishes
   Parameters: none needed
   
7. update_allergy_add/remove - Update customer allergies
   Parameters: allergies (list), reason (for remove)
   
8. no_tool_needed - For greetings, goodbyes, thanks, general chat

9. explain_reasoning - Customer asking why you said/did something
   Parameters: none needed
   
10. handle_misunderstanding - Customer confused or disagrees
    Parameters: none needed
    
11. restaurant_info - Questions about restaurant/service
    Parameters: info_type (hours, location, contact, general)
    
12. change_preference - Customer wants something different
    Parameters: none needed

RULES:
1. Select tools that best answer the customer's request
2. Include all necessary tools (e.g., allergy filter + category search)
3. For get_dish_details: use what the customer said (tool handles fuzzy matching)
4. For categories: use exact category names from the list above
5. For "seafood" requests: use "Seafood" category (includes both fish and shellfish)
6. Return JSON array with tool names and parameters

EXAMPLES:
- "What pasta dishes do you have?" → 
  [{{"tool": "search_by_food_type", "parameters": {{"food_type": "Pasta"}}}}]
  
- "What's for dinner?" → 
  [{{"tool": "search_by_meal_time", "parameters": {{"meal_time": "Dinner"}}}}]
  
- "Show me your starters" → 
  [{{"tool": "search_by_course_type", "parameters": {{"course_type": "starter"}}}}]
  
- "What seafood do you have?" → 
  [{{"tool": "search_by_food_type", "parameters": {{"food_type": "Seafood"}}}}]
  
- "Tell me about the Carbonara" → 
  [{{"tool": "get_dish_details", "parameters": {{"dish_name": "carbonara"}}}}]
  
- "Show me gluten-free pasta" → 
  [{{"tool": "filter_gluten_free"}}, {{"tool": "search_by_food_type", "parameters": {{"food_type": "Pasta"}}}}]
  
- "I'm allergic to nuts" → 
  [{{"tool": "update_allergy_add", "parameters": {{"allergies": ["nuts"]}}}}]
  
- "Thanks" → 
  [{{"tool": "no_tool_needed"}}]
  
- "Goodbye" or "See you soon" → 
  [{{"tool": "no_tool_needed"}}]
  
- "Why do you offer me pasta?" → 
  [{{"tool": "explain_reasoning"}}]
  
- "I didn't ask for that" → 
  [{{"tool": "handle_misunderstanding"}}]
  
- "What time do you close?" → 
  [{{"tool": "restaurant_info", "parameters": {{"info_type": "hours"}}}}]
  
- "Show me something else" → 
  [{{"tool": "change_preference"}}]

IMPORTANT: 
- If customer questions your suggestions ("why do you..."), use explain_reasoning NOT food search tools.
- ONLY use the tools listed above. Do NOT use any other tools like "no_food_response" or others.
- For goodbyes, use "no_tool_needed"

Respond with ONLY the JSON array."""
    
    return prompt

def execute_tool(tool_data: Dict, menu_items: List[Dict], customer_profile: Optional[Any] = None) -> Dict:
    """Execute a tool with given parameters"""
    tool_name = tool_data.get("tool")
    params = tool_data.get("parameters", {})
    
    logger.info(f"execute_tool called: tool={tool_name}, menu_items count={len(menu_items)}")
    
    # Get customer allergies if profile exists
    customer_allergies = []
    if customer_profile:
        customer_allergies = getattr(customer_profile, 'allergies', []) or []
        dietary_restrictions = getattr(customer_profile, 'dietary_restrictions', []) or []
        customer_allergies.extend(dietary_restrictions)
        customer_allergies = [str(a).lower() for a in customer_allergies if a]
        logger.info(f"Customer allergies in execute_tool: {customer_allergies}")
    
    def is_safe_for_customer(item: Dict) -> bool:
        """Check if item is safe based on customer allergies"""
        if not customer_allergies:
            return True
        
        item_allergens = [a.lower() for a in item.get('allergens', [])]
        ingredients_text = ' '.join(item.get('ingredients', [])).lower()
        
        for allergy in customer_allergies:
            allergy_lower = allergy.lower()
            # Check allergens list
            if any(allergy_lower in allergen for allergen in item_allergens):
                return False
            # Check ingredients
            if allergy_lower in ingredients_text:
                return False
        
        return True
    
    if tool_name == "no_tool_needed":
        return {"info": "No execution needed"}
    
    elif tool_name == "get_dish_details":
        dish_name = params.get("dish_name", "").lower().strip()
        
        # First try exact match
        for item in menu_items:
            item_name = (item.get('dish', '') or item.get('name', '')).lower()
            if dish_name == item_name:
                return {
                    "tool": tool_name,
                    "found": True,
                    "dish": {
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "description": item.get('description'),
                        "ingredients": item.get('ingredients', []),
                        "allergens": item.get('allergens', [])
                    }
                }
        
        # Try partial match (e.g., "carbonara" for "Spaghetti Carbonara")
        matches = []
        for item in menu_items:
            item_name = (item.get('dish', '') or item.get('name', '')).lower()
            
            # Check if search term is contained in dish name
            if dish_name in item_name:
                matches.append(item)
            # Check if all words in search are in dish name (handles reordering)
            elif all(word in item_name for word in dish_name.split()):
                matches.append(item)
        
        # If exactly one match, return it
        if len(matches) == 1:
            item = matches[0]
            return {
                "tool": tool_name,
                "found": True,
                "dish": {
                    "name": item.get('dish') or item.get('name'),
                    "price": item.get('price'),
                    "description": item.get('description'),
                    "ingredients": item.get('ingredients', []),
                    "allergens": item.get('allergens', [])
                }
            }
        
        # If multiple matches, return not found (ambiguous)
        elif len(matches) > 1:
            return {
                "tool": tool_name, 
                "found": False, 
                "error": f"Multiple dishes match '{params.get('dish_name')}'. Please be more specific.",
                "suggestions": [m.get('dish') or m.get('name') for m in matches[:3]]
            }
        
        # Try fuzzy matching for spelling mistakes
        from difflib import get_close_matches
        all_dish_names = [(item.get('dish') or item.get('name')) for item in menu_items]
        close_matches = get_close_matches(params.get("dish_name"), all_dish_names, n=3, cutoff=0.7)
        
        if close_matches:
            # Get the best match
            best_match = close_matches[0]
            for item in menu_items:
                if (item.get('dish') or item.get('name')) == best_match:
                    return {
                        "tool": tool_name,
                        "found": True,
                        "corrected": True,
                        "original_query": params.get("dish_name"),
                        "dish": {
                            "name": item.get('dish') or item.get('name'),
                            "price": item.get('price'),
                            "description": item.get('description'),
                            "ingredients": item.get('ingredients', []),
                            "allergens": item.get('allergens', [])
                        }
                    }
        
        return {"tool": tool_name, "found": False, "error": "Dish not found"}
    
    elif tool_name == "search_menu_by_ingredient":
        ingredient = params.get("ingredient", "").lower()
        results = []
        
        for item in menu_items:
            if any(ingredient in ing.lower() for ing in item.get('ingredients', [])):
                # Check allergen safety - BACKEND PRE-FILTERING
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "allergens": item.get('allergens', []),
                        "ingredients": item.get('ingredients', []),
                        "is_nut_free": item.get('is_nut_free', True),
                        "is_dairy_free": item.get('is_dairy_free', False),
                        "is_gluten_free": item.get('is_gluten_free', False),
                        "is_vegan": item.get('is_vegan', False),
                        "is_vegetarian": item.get('is_vegetarian', False)
                    })
        
        return {
            "tool": tool_name,
            "ingredient": params.get("ingredient"),
            "found": len(results),
            "items": results,
            "pre_filtered": customer_allergies is not None and len(customer_allergies) > 0
        }
    
    elif tool_name == "search_by_meal_time":
        meal_time = params.get("meal_time", "").lower()
        results = []
        
        for item in menu_items:
            item_category = item.get('category', '').lower()
            
            if meal_time in item_category:
                # Check allergen safety - BACKEND PRE-FILTERING
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "allergens": item.get('allergens', []),
                        "ingredients": item.get('ingredients', []),
                        "is_nut_free": item.get('is_nut_free', True),
                        "is_dairy_free": item.get('is_dairy_free', False),
                        "is_gluten_free": item.get('is_gluten_free', False),
                        "is_vegan": item.get('is_vegan', False),
                        "is_vegetarian": item.get('is_vegetarian', False)
                    })
        
        return {
            "tool": tool_name,
            "meal_time": params.get("meal_time"),
            "found": len(results),
            "items": results,
            "pre_filtered": customer_allergies is not None and len(customer_allergies) > 0
        }
    
    elif tool_name == "search_by_course_type":
        course_type = params.get("course_type", "").lower()
        results = []
        
        for item in menu_items:
            item_subcategory = item.get('subcategory', '').lower()
            
            if course_type in item_subcategory:
                # Check allergen safety - BACKEND PRE-FILTERING
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "allergens": item.get('allergens', []),
                        "ingredients": item.get('ingredients', []),
                        "is_nut_free": item.get('is_nut_free', True),
                        "is_dairy_free": item.get('is_dairy_free', False),
                        "is_gluten_free": item.get('is_gluten_free', False),
                        "is_vegan": item.get('is_vegan', False),
                        "is_vegetarian": item.get('is_vegetarian', False)
                    })
        
        return {
            "tool": tool_name,
            "course_type": params.get("course_type"),
            "found": len(results),
            "items": results,
            "pre_filtered": customer_allergies is not None and len(customer_allergies) > 0
        }
    
    elif tool_name == "search_by_food_type":
        food_type = params.get("food_type", "").lower()
        results = []
        
        # Debug total items being searched
        logger.info(f"search_by_food_type: Searching for '{food_type}' in {len(menu_items)} items")
        
        for item in menu_items:
            # Check both single category and array of categories
            item_categories = item.get('restaurant_categories', [])
            single_category = item.get('restaurant_category', '')
            
            # Convert to lowercase for comparison
            categories_lower = [cat.lower() for cat in item_categories]
            single_category_lower = single_category.lower()
            
            # Check if food_type matches any category
            if food_type in categories_lower or food_type == single_category_lower:
                # Debug logging for seafood + shellfish allergy case
                if food_type == "seafood" and customer_allergies and "shellfish" in customer_allergies:
                    dish_name = item.get('dish', 'Unknown')
                    item_allergens = item.get('allergens', [])
                    is_safe = is_safe_for_customer(item)
                    logger.info(f"Seafood item '{dish_name}': categories={categories_lower}, allergens={item_allergens}, safe={is_safe}")
                    
                    # Extra debug for fish items
                    if 'fish' in categories_lower:
                        logger.info(f"  -> This is a FISH item, should be safe for shellfish allergy")
                
                # Check allergen safety - BACKEND PRE-FILTERING
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "allergens": item.get('allergens', []),
                        "ingredients": item.get('ingredients', []),
                        "is_nut_free": item.get('is_nut_free', True),
                        "is_dairy_free": item.get('is_dairy_free', False),
                        "is_gluten_free": item.get('is_gluten_free', False),
                        "is_vegan": item.get('is_vegan', False),
                        "is_vegetarian": item.get('is_vegetarian', False)
                    })
        
        # More debug logging
        if food_type == "seafood" and customer_allergies and "shellfish" in customer_allergies:
            logger.info(f"Seafood search with shellfish allergy: found {len(results)} safe items")
            if len(results) == 0:
                logger.warning("No seafood items passed safety check! This is likely a bug.")
        
        return {
            "tool": tool_name,
            "food_type": params.get("food_type"),
            "found": len(results),
            "items": results,
            "pre_filtered": customer_allergies is not None and len(customer_allergies) > 0
        }
    
    elif tool_name in ["filter_vegetarian", "filter_vegan", "filter_gluten_free", "filter_nut_free", "filter_dairy_free", "filter_shellfish_free"]:
        filter_type = tool_name.replace("filter_", "").replace("_", "-")
        results = []
        
        # Debug logging
        if filter_type == "shellfish-free":
            logger.info(f"Executing shellfish-free filter. Total menu items: {len(menu_items)}")
            logger.info(f"Customer allergies: {customer_allergies}")
        
        for item in menu_items:
            suitable = False
            
            # Use the boolean fields when available
            if filter_type == "nut-free" and item.get('is_nut_free', True):
                suitable = True
            elif filter_type == "dairy-free" and item.get('is_dairy_free', False):
                suitable = True
            elif filter_type == "gluten-free" and item.get('is_gluten_free', False):
                suitable = True
            elif filter_type == "vegetarian" and item.get('is_vegetarian', False):
                suitable = True
            elif filter_type == "vegan" and item.get('is_vegan', False):
                suitable = True
            elif filter_type == "shellfish-free":
                # No boolean field for shellfish, check allergens
                allergens = [a.lower() for a in item.get('allergens', [])]
                if "shellfish" not in allergens:
                    suitable = True
            
            # Also check customer allergies - BACKEND PRE-FILTERING
            if suitable and is_safe_for_customer(item):
                results.append({
                    "name": item.get('dish') or item.get('name'),
                    "price": item.get('price'),
                    "allergens": item.get('allergens', []),
                    "ingredients": item.get('ingredients', []),
                    "is_nut_free": item.get('is_nut_free', True),
                    "is_dairy_free": item.get('is_dairy_free', False),
                    "is_gluten_free": item.get('is_gluten_free', False),
                    "is_vegan": item.get('is_vegan', False),
                    "is_vegetarian": item.get('is_vegetarian', False)
                })
        
        # Debug logging
        if filter_type == "shellfish-free":
            logger.info(f"Shellfish-free filter found {len(results)} items before limiting to 15")
        
        return {
            "tool": tool_name,
            "filter": filter_type,
            "found": len(results),
            "items": results  # Remove limit - let intersection logic handle it
        }
    
    elif tool_name in ["update_allergy_add", "update_allergy_remove"]:
        # These are handled separately in the main function
        return {"tool": tool_name, "action": "pending", "allergies": params.get("allergies", [])}
    
    elif tool_name == "no_food_response":
        # Handle MIA backend hallucinating this tool from v6/v7 usage
        # Treat it as no_tool_needed to prevent fallback
        logger.warning("MIA selected non-existent 'no_food_response' tool - treating as no_tool_needed")
        return {"info": "No execution needed", "tool": tool_name}
    
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def execute_non_food_tool(tool_name: str, params: Dict, customer_profile: Optional[Any] = None) -> Dict:
    """Execute non-food related tools that don't need menu context"""
    
    # Get customer restrictions for context (but won't suggest food)
    has_restrictions = False
    restriction_info = []
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary = getattr(customer_profile, 'dietary_restrictions', []) or []
        restriction_info = allergies + dietary
        has_restrictions = bool(restriction_info)
    
    if tool_name == "explain_reasoning":
        return {
            "tool": tool_name,
            "response_type": "explanation_needed",
            "context": "Customer questioning AI behavior",
            "has_dietary_restrictions": has_restrictions,
            "restrictions": restriction_info,
            "do_not_suggest_food": True
        }
    
    elif tool_name == "handle_misunderstanding":
        return {
            "tool": tool_name,
            "response_type": "clarification_needed",
            "context": "Customer seems confused or disagrees",
            "has_dietary_restrictions": has_restrictions,
            "restrictions": restriction_info,
            "do_not_suggest_food": True
        }
    
    elif tool_name == "restaurant_info":
        info_type = params.get("info_type", "general")
        info_map = {
            "hours": "Mon-Thu: 11:30 AM - 10:00 PM, Fri-Sat: 11:30 AM - 11:00 PM, Sun: 10:00 AM - 9:00 PM",
            "location": "Located in the heart of downtown at 123 Main Street",
            "contact": "Phone: (555) 123-4567, Email: info@bellavista.com",
            "general": "Bella Vista is a modern Italian restaurant serving authentic cuisine since 2015"
        }
        return {
            "tool": tool_name,
            "info_type": info_type,
            "info": info_map.get(info_type, info_map["general"]),
            "has_dietary_restrictions": has_restrictions,
            "do_not_suggest_food": True
        }
    
    elif tool_name == "change_preference":
        return {
            "tool": tool_name,
            "response_type": "preference_change",
            "context": "Customer wants different options",
            "has_dietary_restrictions": has_restrictions,
            "restrictions": restriction_info,
            "do_not_suggest_food": False  # This one might involve food suggestions
        }
    
    elif tool_name == "no_food_response":
        # Handle MIA backend hallucinating this tool from v6/v7 usage
        response_type = params.get("response_type", "greeting")
        return {
            "tool": tool_name,
            "response_type": response_type,
            "do_not_suggest_food": True,
            "suppress_allergies": True,
            "info": "No execution needed"  # Add this to prevent fallback
        }
    
    else:
        return {"error": f"Unknown non-food tool: {tool_name}"}

def execute_tools_single_pass(tools: List[Dict], menu_items: List[Dict], customer_profile: Optional[Any]) -> List[Dict]:
    """Execute multiple search/filter tools in a single pass for performance"""
    logger.info(f"Executing {len(tools)} tools in single pass over {len(menu_items)} items")
    
    # Get customer allergies once
    customer_allergies = []
    if customer_profile:
        customer_allergies = getattr(customer_profile, 'allergies', []) or []
        dietary_restrictions = getattr(customer_profile, 'dietary_restrictions', []) or []
        customer_allergies.extend(dietary_restrictions)
        customer_allergies = [str(a).lower() for a in customer_allergies if a]
    
    # Initialize results for each tool
    tool_results = []
    for tool_data in tools:
        tool_results.append({
            "tool": tool_data.get("tool"),
            "parameters": tool_data.get("parameters", {}),
            "items": [],
            "pre_filtered": len(customer_allergies) > 0
        })
    
    # Single pass through all menu items
    for item in menu_items:
        # Check safety ONCE per item
        if customer_allergies:
            item_allergens = [a.lower() for a in item.get('allergens', [])]
            ingredients_text = ' '.join(item.get('ingredients', [])).lower()
            
            is_safe = True
            for allergy in customer_allergies:
                if any(allergy in allergen for allergen in item_allergens) or allergy in ingredients_text:
                    is_safe = False
                    break
            
            if not is_safe:
                continue  # Skip unsafe items
        
        # Now check this safe item against each tool's criteria
        for i, tool_data in enumerate(tools):
            tool_name = tool_data.get("tool")
            params = tool_data.get("parameters", {})
            
            # Format item result once (will be reused if item matches multiple tools)
            item_result = {
                "name": item.get('dish') or item.get('name'),
                "price": item.get('price'),
                "allergens": item.get('allergens', []),
                "ingredients": item.get('ingredients', []),
                "is_nut_free": item.get('is_nut_free', True),
                "is_dairy_free": item.get('is_dairy_free', False),
                "is_gluten_free": item.get('is_gluten_free', False),
                "is_vegan": item.get('is_vegan', False),
                "is_vegetarian": item.get('is_vegetarian', False)
            }
            
            # Check tool-specific criteria
            if tool_name == "search_by_food_type":
                food_type = params.get("food_type", "").lower()
                item_categories = item.get('restaurant_categories', [])
                single_category = item.get('restaurant_category', '')
                categories_lower = [cat.lower() for cat in item_categories]
                single_category_lower = single_category.lower()
                
                if food_type in categories_lower or food_type == single_category_lower:
                    tool_results[i]["items"].append(item_result)
                    
            elif tool_name == "search_by_meal_time":
                meal_time = params.get("meal_time", "").lower()
                item_category = item.get('category', '').lower()
                if meal_time in item_category:
                    tool_results[i]["items"].append(item_result)
                    
            elif tool_name == "search_by_course_type":
                course_type = params.get("course_type", "").lower()
                item_subcategory = item.get('subcategory', '').lower()
                if course_type in item_subcategory:
                    tool_results[i]["items"].append(item_result)
                    
            elif tool_name == "search_menu_by_ingredient":
                ingredient = params.get("ingredient", "").lower()
                if any(ingredient in ing.lower() for ing in item.get('ingredients', [])):
                    tool_results[i]["items"].append(item_result)
                    
            elif tool_name.startswith("filter_"):
                filter_type = tool_name.replace("filter_", "").replace("_", "-")
                suitable = False
                
                if filter_type == "nut-free" and item.get('is_nut_free', True):
                    suitable = True
                elif filter_type == "dairy-free" and item.get('is_dairy_free', False):
                    suitable = True
                elif filter_type == "gluten-free" and item.get('is_gluten_free', False):
                    suitable = True
                elif filter_type == "vegetarian" and item.get('is_vegetarian', False):
                    suitable = True
                elif filter_type == "vegan" and item.get('is_vegan', False):
                    suitable = True
                elif filter_type == "shellfish-free":
                    allergens = [a.lower() for a in item.get('allergens', [])]
                    if "shellfish" not in allergens:
                        suitable = True
                
                if suitable:
                    tool_results[i]["items"].append(item_result)
    
    # Format final results
    final_results = []
    for i, result in enumerate(tool_results):
        tool_name = result["tool"]
        params = result["parameters"]
        
        if tool_name == "search_by_food_type":
            final_results.append({
                "tool": tool_name,
                "food_type": params.get("food_type"),
                "found": len(result["items"]),
                "items": result["items"],
                "pre_filtered": result["pre_filtered"]
            })
        elif tool_name == "search_by_meal_time":
            final_results.append({
                "tool": tool_name,
                "meal_time": params.get("meal_time"),
                "found": len(result["items"]),
                "items": result["items"],
                "pre_filtered": result["pre_filtered"]
            })
        elif tool_name == "search_by_course_type":
            final_results.append({
                "tool": tool_name,
                "course_type": params.get("course_type"),
                "found": len(result["items"]),
                "items": result["items"],
                "pre_filtered": result["pre_filtered"]
            })
        elif tool_name == "search_menu_by_ingredient":
            final_results.append({
                "tool": tool_name,
                "ingredient": params.get("ingredient"),
                "found": len(result["items"]),
                "items": result["items"],
                "pre_filtered": result["pre_filtered"]
            })
        elif tool_name.startswith("filter_"):
            filter_type = tool_name.replace("filter_", "").replace("_", "-")
            final_results.append({
                "tool": tool_name,
                "filter": filter_type,
                "found": len(result["items"]),
                "items": result["items"],
                "pre_filtered": result["pre_filtered"]
            })
    
    logger.info(f"Single pass execution complete. Found items: {[r['found'] for r in final_results]}")
    return final_results

def build_phase2_prompt(message: str, tool_results: List[Dict], restaurant_name: str, 
                       customer_profile: Any, context_type: str, context_data: Dict,
                       chat_history: List[Dict] = None) -> str:
    """Build Phase 2 prompt for final response generation"""
    
    # Check if any non-food tools were executed
    non_food_tools_executed = any(
        result.get("tool") in ["explain_reasoning", "handle_misunderstanding", "restaurant_info", "change_preference"]
        and result.get("do_not_suggest_food", False)
        for result in tool_results
    )
    
    # Context-specific intro
    if non_food_tools_executed:
        # Non-food context - focus on answering the meta-question without suggesting food
        prompt = f"""You are Maria, a helpful server at {restaurant_name}.

The customer is asking a question that is NOT about ordering food. Focus on answering their specific question.

"""
    elif context_type == "allergen_safety":
        prompt = f"""You are Maria, a safety-conscious server at {restaurant_name}.

CRITICAL: Customer has restrictions: {', '.join(context_data.get('all_restrictions', []))}

"""
    else:
        prompt = f"""You are Maria, a warm and knowledgeable server at {restaurant_name}.

"""
    
    # Add conversation history
    if chat_history and len(chat_history) > 1:
        interaction_count = sum(1 for msg in chat_history if msg["role"] == "assistant")
        
        prompt += "CONVERSATION SO FAR:\n"
        for msg in chat_history[:-1]:
            if msg["role"] == "user":
                prompt += f"Customer: {msg['message']}\n"
            else:
                prompt += f"You: {msg['message']}\n"
        prompt += f"\n[This is message #{interaction_count + 1} in the conversation]\n"
    
    prompt += f"""
Current request: "{message}"

MENU DATA FROM SEARCH:
"""
    
    # Format tool results clearly
    for result in tool_results:
        if result.get("tool") == "no_tool_needed":
            continue
        elif result.get("tool") == "get_dish_details":
            if result.get("found"):
                dish = result["dish"]
                prompt += f"\nDISH DETAILS:\n"
                
                # If spelling was corrected, note it
                if result.get("corrected"):
                    prompt += f"(Found match for '{result.get('original_query')}')\n"
                    
                prompt += f"- {dish['name']} - {dish['price']}\n"
                prompt += f"  {dish['description']}\n"
                if dish.get('allergens'):
                    prompt += f"  Allergens: {', '.join(dish['allergens'])}\n"
            else:
                # Handle dish not found
                prompt += f"\nDISH SEARCH RESULT:\n"
                
                # Check if it's ambiguous (multiple matches)
                if "Multiple dishes match" in result.get("error", ""):
                    prompt += f"❌ {result['error']}\n"
                    if result.get("suggestions"):
                        prompt += f"Did you mean one of these: {', '.join(result['suggestions'])}?\n"
                else:
                    prompt += f"❌ The requested dish was not found in our menu.\n"
        elif "items" in result:
            if result.get("found", 0) > 0:
                # Check if pre-filtered
                if result.get("pre_filtered"):
                    prompt += f"\n{result.get('category', result.get('filter', result.get('food_type', 'SEARCH'))).upper()} RESULTS (pre-filtered for safety):\n"
                else:
                    prompt += f"\n{result.get('category', result.get('filter', result.get('food_type', 'SEARCH'))).upper()} RESULTS:\n"
                    
                for item in result["items"]:
                    prompt += f"- {item['name']} {item['price']}\n"
                    # Always include ingredient and allergen info for safety
                    if item.get('ingredients'):
                        prompt += f"  Ingredients: {', '.join(item['ingredients'])}\n"
                    if item.get('allergens'):
                        prompt += f"  Contains: {', '.join(item['allergens'])}\n"
                    # Include dietary flags
                    dietary_info = []
                    if item.get('is_vegan'):
                        dietary_info.append("Vegan")
                    if item.get('is_vegetarian') and not item.get('is_vegan'):
                        dietary_info.append("Vegetarian")
                    if item.get('is_gluten_free'):
                        dietary_info.append("Gluten-Free")
                    if dietary_info:
                        prompt += f"  Dietary: {', '.join(dietary_info)}\n"
            else:
                # Handle empty filter results
                filter_type = result.get('filter', '')
                if filter_type:
                    prompt += f"\n{filter_type.upper()} SEARCH RESULTS:\n"
                    prompt += f"❌ No {filter_type} options found that meet all criteria.\n"
                else:
                    prompt += f"\n{result.get('category', 'SEARCH')} RESULTS:\n"
                    prompt += f"❌ No items found in this category.\n"
    
    # Response guidelines
    if non_food_tools_executed:
        # Non-food context - special guidelines
        prompt += """
IMPORTANT GUIDELINES FOR NON-FOOD QUESTIONS:
1. DO NOT suggest any food items or dishes
2. DO NOT ask what the customer would like to eat
3. DO NOT recommend menu items
4. Focus ONLY on answering their specific question:
"""
        # Add specific guidelines based on which non-food tool was used
        for result in tool_results:
            if result.get("tool") == "explain_reasoning":
                prompt += """
   - They asked WHY you suggested certain items - explain your reasoning based on their restrictions/preferences
   - Reference the specific allergens or dietary requirements that guided your suggestions
"""
            elif result.get("tool") == "handle_misunderstanding":
                prompt += """
   - They seem confused or there's a misunderstanding - clarify what you meant
   - Be patient and helpful in clearing up any confusion
"""
            elif result.get("tool") == "restaurant_info":
                prompt += """
   - They want information about the restaurant - provide relevant details
   - This might include hours, policies, location, or general information
"""
            elif result.get("tool") == "change_preference":
                prompt += """
   - They want to change their preferences or restrictions
   - Acknowledge the change and confirm you'll remember it
"""
        
        prompt += """
5. Keep response concise and directly address their question
6. After answering, do NOT transition back to suggesting food unless they explicitly ask
"""
    elif context_type == "allergen_safety":
        customer_allergies = getattr(customer_profile, 'allergies', []) if customer_profile else []
        prompt += f"""
SAFETY RULES:
1. Results shown are pre-filtered for customer safety. 
   - Trust the data provided, but always check the "Contains" and "Ingredients" fields before confirming.
2. Never invent or modify information.
   - No new dishes, no fake prices, no new allergens, no new dietary labels.
3. A dish is SAFE if it does not contain the customer's allergens.
   A dish is UNSAFE if the allergen is explicitly listed.
   A dish is UNKNOWN if not listed in menu results — politely say it's not available.
4. If allergen might reasonably appear in an ingredient but isn't listed, say:
   "Based on the provided menu data, this dish does not list [allergen], but I recommend double-checking with staff for your safety."
5. Responses must be concise (2–3 sentences max).
   - Use exact dish names and prices.
   - Use short lists for multiple dishes.
6. Always continue applying allergy/dietary filters from Phase 1.
7. Stay natural, warm, and professional — but never compromise on menu accuracy or safety.

Customer is allergic to: {', '.join(customer_allergies) if customer_allergies else 'nothing specified'}
"""
    else:
        prompt += """
RESPONSE GUIDELINES:
- Use EXACT dish names and prices from the menu data above
- Keep response concise (2-3 sentences max)
- NEVER say "Hello" if already greeted
- If listing multiple items, include prices for each
- Be natural and helpful
- IMPORTANT: If a dish was not found, politely inform the customer we don't have that item
- NEVER invent or suggest dishes that aren't in the search results above
- If NO items were found for a dietary filter, explain that we don't have options that meet ALL their restrictions
- When filters return empty, suggest checking individual restrictions or offer alternatives
"""
    
    prompt += "\nRespond naturally:"
    
    return prompt

def generate_response_internal_tools_v5(req: Any, db: Session) -> Any:
    """2-Phase flow: Tool selection with params → Response generation"""
    from schemas.chat import ChatResponse
    
    try:
        start_time = time.time()
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            from sqlalchemy import text
            result = db.execute(
                text("SELECT data FROM businesses WHERE business_id = :id"),
                {"id": req.restaurant_id}
            ).fetchone()
            
            if result:
                restaurant_data = result[0] if isinstance(result[0], dict) else json.loads(result[0])
            else:
                return ChatResponse(answer="Restaurant not found", response_id=None, confidence_score=0.0)
        else:
            restaurant_data = json.loads(restaurant.data) if isinstance(restaurant.data, str) else restaurant.data
        
        menu_items = restaurant_data.get('menu', [])
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        
        # Get context
        customer_profile = get_customer_profile(db, req.client_id, req.restaurant_id)
        chat_history = get_chat_history(db, req.client_id, req.restaurant_id, limit=3)
        context_type, context_data = get_context_type(customer_profile, req.message)
        
        logger.info(f"=== V5 2-Phase System - Restaurant: {req.restaurant_id} ===")
        logger.info(f"Context: {context_type}, Menu items: {len(menu_items)}")
        
        # === PHASE 1: Tool Selection WITH Parameters ===
        logger.info("PHASE 1: Tool selection with parameters")
        phase1_prompt = build_phase1_prompt(req.message, customer_profile, chat_history, menu_items, restaurant_name)
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": phase1_prompt,
                "max_tokens": 200,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return ChatResponse(answer="I'm having trouble understanding. Please try again.", response_id=None, confidence_score=0.0)
        
        # Parse tool selection with parameters
        response_data = response.json()
        selection_text = response_data.get("response", "")
        
        # Handle None case (when MIA returns {"response": null})
        if selection_text is None:
            selection_text = ""
        
        selection_text = selection_text.strip()
        
        try:
            selected_tools = json.loads(selection_text)
            if not isinstance(selected_tools, list):
                selected_tools = [{"tool": "no_tool_needed"}]
        except:
            selected_tools = [{"tool": "no_tool_needed"}]
        
        logger.info(f"Selected tools with params: {selected_tools}")
        
        # Handle simple flow (no tools needed)
        if len(selected_tools) == 1 and selected_tools[0].get("tool") == "no_tool_needed":
            # Check if this is a goodbye message
            goodbye_keywords = ["goodbye", "bye", "see you", "later", "take care", "have a good"]
            is_goodbye = any(keyword in req.message.lower() for keyword in goodbye_keywords)
            
            simple_prompt = f"""You are Maria at {restaurant_name}.

"""
            if customer_profile:
                allergies = getattr(customer_profile, 'allergies', []) or []
                if allergies:
                    simple_prompt += f"CUSTOMER INFO: Allergic to {', '.join(allergies)}\n\n"
            
            if chat_history and len(chat_history) > 1:
                simple_prompt += "RECENT CONVERSATION:\n"
                for msg in chat_history[-3:-1]:
                    role = "Customer" if msg["role"] == "user" else "You"
                    simple_prompt += f"{role}: {msg['message']}\n"
                simple_prompt += "\n"
            
            if is_goodbye:
                simple_prompt += f"""Current message: "{req.message}"

GUIDELINES:
- This is a goodbye/farewell message
- Be warm and friendly
- Thank them for their visit/interest
- DO NOT suggest any menu items or mention food
- Keep it brief (1-2 sentences)

Respond:"""
            else:
                menu_summary = create_menu_summary(menu_items)
                simple_prompt += f"""MENU INFORMATION:
{menu_summary}

Current message: "{req.message}"

GUIDELINES:
- Be concise (2-3 sentences max)
- Use exact prices from menu
- {"Greet warmly ONCE" if not chat_history or len(chat_history) <= 1 else "NO greeting"}
- Be helpful and natural

Respond:"""
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={"message": simple_prompt, "max_tokens": 200},
                timeout=30
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "")
                
                # Always add debug info
                debug_info = {
                    "flow": "simple (no_tool_needed)",
                    "is_goodbye": is_goodbye,
                    "menu_summary_length": 0 if is_goodbye else len(menu_summary),
                    "context_type": context_type,
                    "customer_allergies": getattr(customer_profile, 'allergies', []) if customer_profile else [],
                    "response_time": f"{time.time() - start_time:.2f}s"
                }
                answer = f"{answer}\n\n[DEBUG INFO]\n{json.dumps(debug_info, indent=2)}"
                
                return ChatResponse(
                    answer=answer,
                    response_id=response.json().get("job_id"),
                    confidence_score=0.85
                )
        
        # === Process Allergy Updates FIRST ===
        # This ensures the profile is updated before other tools use it
        for tool_data in selected_tools:
            if tool_data.get("tool") in ["update_allergy_add", "update_allergy_remove"]:
                try:
                    allergies = tool_data.get("parameters", {}).get("allergies", [])
                    
                    if tool_data["tool"] == "update_allergy_add":
                        # Add allergies to profile
                        if customer_profile:
                            existing_allergies = set(customer_profile.allergies or [])
                            existing_allergies.update(allergies)
                            customer_profile.allergies = list(existing_allergies)
                            db.commit()
                            logger.info(f"Added allergies to profile: {allergies}. Profile now has: {customer_profile.allergies}")
                    else:
                        # Remove allergies from profile
                        if customer_profile:
                            existing_allergies = set(customer_profile.allergies or [])
                            for allergy in allergies:
                                existing_allergies.discard(allergy)
                            customer_profile.allergies = list(existing_allergies)
                            db.commit()
                            logger.info(f"Removed allergies from profile: {allergies}. Profile now has: {customer_profile.allergies}")
                except Exception as e:
                    logger.error(f"Failed to process allergy update: {e}")
        
        # === Execute Tools Locally ===
        tool_results = []
        logger.info(f"Executing {len(selected_tools)} tools. Menu has {len(menu_items)} items")
        
        # Define non-food tools that don't need menu context
        NON_FOOD_TOOLS = ["explain_reasoning", "handle_misunderstanding", "restaurant_info", "change_preference"]
        
        # Separate tools by type for efficient execution
        search_filter_tools = []
        other_tools = []
        non_food_tools = []
        
        for tool_data in selected_tools:
            tool_name = tool_data.get("tool")
            if tool_name in ["update_allergy_add", "update_allergy_remove"]:
                # Already processed above, just add result
                action = "added" if tool_name == "update_allergy_add" else "removed"
                allergies = tool_data.get("parameters", {}).get("allergies", [])
                result = {"success": True, "action": action, "allergies": allergies, "tool": tool_name}
                tool_results.append(result)
            elif tool_name in ["search_by_food_type", "search_by_meal_time", "search_by_course_type", 
                             "search_menu_by_ingredient", "filter_vegetarian", "filter_vegan", 
                             "filter_gluten_free", "filter_nut_free", "filter_dairy_free", "filter_shellfish_free"]:
                search_filter_tools.append(tool_data)
            elif tool_name in NON_FOOD_TOOLS:
                non_food_tools.append(tool_data)
            else:
                other_tools.append(tool_data)
        
        # Execute non-food tools first (they don't need menu data)
        for tool_data in non_food_tools:
            tool_name = tool_data.get("tool")
            params = tool_data.get("parameters", {})
            result = execute_non_food_tool(tool_name, params, customer_profile)
            tool_results.append(result)
            logger.info(f"Non-food tool {tool_name} executed")
        
        # Execute search/filter tools in single pass for performance
        if search_filter_tools:
            search_results = execute_tools_single_pass(search_filter_tools, menu_items, customer_profile)
            tool_results.extend(search_results)
        
        # Execute other tools individually (get_dish_details, no_tool_needed, etc)
        for tool_data in other_tools:
            result = execute_tool(tool_data, menu_items, customer_profile)
            tool_results.append(result)
            logger.info(f"Tool {tool_data.get('tool')} returned: found={result.get('found', 'N/A')}")
        
        # Check if all searches returned no results (except allergen filters)
        all_empty = True
        has_allergen_filter = False
        
        for i, tool_data in enumerate(selected_tools):
            tool_name = tool_data.get("tool")
            result = tool_results[i]
            
            # Check if this is an allergen filter
            if tool_name in ["filter_vegetarian", "filter_vegan", "filter_gluten_free", "filter_nut_free", "filter_dairy_free", "filter_shellfish_free"]:
                has_allergen_filter = True
            
            # Check if this search returned results
            if result.get("found", 0) > 0 or result.get("info") == "No execution needed":
                all_empty = False
                break
        
        # FALLBACK: If no results and NOT allergen-related, use simple flow with full menu
        if all_empty and not has_allergen_filter and context_type != "allergen_safety":
            logger.info("No results from tools, falling back to simple flow with full menu")
            
            menu_summary = create_menu_summary(menu_items)
            
            fallback_prompt = f"""You are Maria at {restaurant_name}.

The customer asked: "{req.message}"

No specific matches were found, but here's our full menu to help you answer:

{menu_summary}

INSTRUCTIONS:
- The search tools found no exact matches, but check the full menu above
- If they asked for a specific dish (like pesto, pizza, etc) that's not in our menu, politely say we don't have it
- Suggest similar items or alternatives based on what they asked for
- DO NOT pretend we have dishes that aren't listed above
- Use exact prices from the menu
- Be helpful and explain what options are available
- Keep response concise (2-3 sentences)

Respond:"""
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={"message": fallback_prompt, "max_tokens": 200},
                timeout=30
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "")
                
                # Always add debug info
                debug_info = {
                    "flow": "fallback (no results from tools)",
                    "phase1_tools_selected": selected_tools,
                    "tool_results": tool_results,
                    "menu_summary_length": len(menu_summary),
                    "context_type": context_type,
                    "customer_allergies": getattr(customer_profile, 'allergies', []) if customer_profile else [],
                    "response_time": f"{time.time() - start_time:.2f}s"
                }
                answer = f"{answer}\n\n[DEBUG INFO]\n{json.dumps(debug_info, indent=2)}"
                
                return ChatResponse(
                    answer=answer,
                    response_id=response.json().get("job_id"),
                    confidence_score=0.8
                )
        
        # (Allergy updates already processed above, removed duplicate code)
        
        # === Apply Intersection Logic for Multiple Search/Filter Tools ===
        # Count search/filter tools first
        search_filter_indices = []
        
        for i, result in enumerate(tool_results):
            tool_name = result.get("tool", "")
            if ("items" in result or "results" in result) and tool_name not in ["update_allergy_add", "update_allergy_remove", "get_dish_details", "no_tool_needed"]:
                search_filter_indices.append(i)
        
        # Only apply intersection if multiple search/filter tools were used
        if len(search_filter_indices) <= 1:
            logger.info("Skipping intersection logic - only one or no search/filter tool used")
        else:
            # If multiple search/filter tools are used, only keep items that appear in ALL results
            all_item_names = []
            
            for idx in search_filter_indices:
                result = tool_results[idx]
                items = result.get("items", result.get("results", []))
                if items:
                    # Extract item names from this tool's results
                    item_names = set()
                    for item in items:
                        name = item.get("name", item.get("dish", ""))
                        if name:
                            item_names.add(name)
                    all_item_names.append(item_names)
        
            # If we have multiple search/filter tools, apply intersection
            if len(all_item_names) > 1:
                logger.info(f"Applying intersection logic for {len(all_item_names)} search/filter tools")
            
                # Debug: log what each tool found
                for i, names in enumerate(all_item_names):
                    tool_idx = search_filter_indices[i]
                    tool_name = tool_results[tool_idx].get("tool", "unknown")
                    logger.info(f"Tool {tool_name} found {len(names)} items: {list(names)[:5]}...")
                
                # Special case: if one of the tools is shellfish-free filter and customer has shellfish allergy
                # This is redundant and might cause issues
                customer_allergies = []
                if customer_profile:
                    customer_allergies = [str(a).lower() for a in getattr(customer_profile, 'allergies', []) if a]
                
                has_shellfish_allergy = customer_allergies and 'shellfish' in customer_allergies
                has_shellfish_filter = any(tool_results[idx].get("tool") == "filter_shellfish_free" for idx in search_filter_indices)
                
                if has_shellfish_allergy and has_shellfish_filter:
                    logger.warning("Customer already has shellfish allergy, shellfish-free filter is redundant")
                
                # Find items that appear in ALL result sets
                intersected_names = all_item_names[0]
                for names in all_item_names[1:]:
                    intersected_names = intersected_names.intersection(names)
                
                logger.info(f"Intersection result: {len(intersected_names)} items found in all result sets")
                if intersected_names:
                    logger.info(f"Intersected items: {list(intersected_names)[:10]}")
                
                # Update each tool's results to only include intersected items
                for idx in search_filter_indices:
                    result = tool_results[idx]
                    items_key = "items" if "items" in result else "results"
                    original_items = result[items_key]
                
                    # Filter to only intersected items
                    filtered_items = []
                    for item in original_items:
                        name = item.get("name", item.get("dish", ""))
                        if name in intersected_names:
                            filtered_items.append(item)
                    
                    result[items_key] = filtered_items
                    result["found"] = len(filtered_items)
                    
                    logger.info(f"Tool {result.get('tool')}: filtered from {len(original_items)} to {len(filtered_items)} items")
        
        # === PHASE 2: Generate Response ===
        logger.info("PHASE 2: Generating response from tool results")
        
        phase2_prompt = build_phase2_prompt(
            req.message,
            tool_results,
            restaurant_name,
            customer_profile,
            context_type,
            context_data,
            chat_history
        )
        
        final_response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={"message": phase2_prompt, "max_tokens": 300},
            timeout=30
        )
        
        if final_response.status_code == 200:
            answer = final_response.json().get("response", "")
            
            # Extract customer info if mentioned
            message_lower = req.message.lower()
            if any(word in message_lower for word in ['allergic', 'intolerant', "can't eat", 'allergy']):
                name_patterns = ["i'm", "i am", "my name is", "call me"]
                for pattern in name_patterns:
                    if pattern in message_lower:
                        parts = message_lower.split(pattern)
                        if len(parts) > 1:
                            potential_name = parts[1].strip().split()[0]
                            if len(potential_name) > 2 and potential_name.replace('-', '').isalpha():
                                logger.info(f"Extracted customer info: name={potential_name}, has allergies")
            
            
            # Always add debug info
            debug_info = {
                "flow": "tool_flow",
                "phase1_tools_selected": [{"tool": t.get("tool"), "params": t.get("parameters", {})} for t in selected_tools],
                "tool_results_summary": [
                    {
                        "tool": r.get("tool"),
                        "items_found": len(r.get("results", r.get("items", []))) if ("results" in r or "items" in r) else r.get("found", "N/A"),
                        "found": r.get("found", None)
                    } for r in tool_results
                ],
                "context_type": context_type,
                "customer_allergies": getattr(customer_profile, 'allergies', []) if customer_profile else [],
                "response_time": f"{time.time() - start_time:.2f}s"
            }
            answer_with_debug = f"{answer}\n\n[DEBUG INFO]\n{json.dumps(debug_info, indent=2)}"
            
            return ChatResponse(
                answer=answer_with_debug,
                response_id=final_response.json().get("job_id"),
                confidence_score=0.9
            )
        
        return ChatResponse(answer="I'm having trouble with that request.", response_id=None, confidence_score=0.0)
        
    except Exception as e:
        logger.error(f"V5 2-Phase error: {e}", exc_info=True)
        return ChatResponse(
            answer="I apologize, but I'm having technical difficulties. Please try again.",
            response_id=None,
            confidence_score=0.0
        )

def mia_chat_service_internal_tools_v5(req: Any, db: Session) -> Any:
    return generate_response_internal_tools_v5(req, db)