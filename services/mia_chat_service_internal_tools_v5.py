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
    """Build deterministic Phase 1 prompt based on rule-based system"""
    
    # Get available data
    categories = get_available_categories(menu_items)
    dish_names = get_available_dish_names(menu_items)
    
    # DEBUG: Log available categories
    logger.info(f"=== PHASE 1 PROMPT BUILD ===")
    logger.info(f"Available food categories: {categories.get('food_categories', [])}")
    logger.info(f"Menu has {len(menu_items)} items")
    logger.info(f"Message to process: '{message}'")
    
    # Get current allergies
    current_allergies = []
    if customer_profile:
        current_allergies = [str(a).lower().strip() for a in (getattr(customer_profile, 'allergies', []) or [])]
    
    prompt = f"""You are **ToolSelector**. Decide which tool to call for a restaurant chatbot.

**Inputs:**
* last_user_message: "{message}"
* current_profile_allergies: {json.dumps(current_allergies)}

**Output:** Return **only** a JSON **array** (1 item) describing the tool call. **Never** return an empty array.

## Allowed tools (exact names)

* `search_by_food_type` {{ "food_type": TitleCase string }}
* `get_dish_details` {{ "dish_name": string }}
* `search_by_meal_time` {{ "meal_time": one of ["Breakfast","Lunch","Dinner","Brunch","Late Night"] }}
* `search_by_course_type` {{ "course": one of ["Appetizer","Main","Dessert","Side","Drink"] }}
* `search_menu_by_ingredient` {{ "ingredient": TitleCase string }}
* `filter_dietary` {{ "diet": one of ["Vegetarian","Vegan","Gluten-Free","Halal","Kosher","Keto","Pescatarian"] }}
* `filter_dietary_food_type` {{ "diet": [TitleCase], "food_type": TitleCase }}
* `search_menu_general` {{ "scope": one of ["menu","popular","recommendations","specials"], "message_context": "original user message for context inference" }}
* `restaurant_info` {{ "topic": one of ["hours","location","contact","parking","greeting"] }}
* `update_allergy_add` {{ "allergies": [lowercase string] }}
* `update_allergy_remove` {{ "allergies": [lowercase string] }}
* `ask_clarify` {{ "question": string }}
* `check_meal_availability` {{ "meal_type": one of ["breakfast","lunch","dinner","brunch"] }}

Output must be a **single-element** JSON array:
[{{
  "tool": "<one of the above>",
  "parameters": {{ ... }}
}}]

**Never** return `[]`.

## Decision rules (apply top-down)

1. **Ambiguity check first**
   - "remove [allergen]" (just these two words) -> `ask_clarify`
   - "no [allergen]" (just these two words) -> `ask_clarify`
   - "[allergen]" alone -> `ask_clarify`
   - "without [allergen]" (unclear context) -> `ask_clarify`

2. **Allergy mention gate (strict)**
   If message explicitly mentions allergies/restrictions ("allergic", "allergy", "intolerance", "no longer allergic", "remove from my allergies", "I can/can't eat X"):
   - **Simple removal**: "not/no longer allergic to X", "remove X from my allergies", "I'm fine with X now" -> `update_allergy_remove` {{ "allergies": ["x"] }}
   - **Correction/replacement**: "not allergic to X, allergic to Y", "meant Y not X" -> First `update_allergy_remove` {{ "allergies": ["x"] }}
   - **Addition only**: "I'm allergic to X", "add X to my allergies" -> `update_allergy_add` {{ "allergies": ["x"] }}
   When any allergy rule triggers, do **not** choose a menu/search tool.

3. **Restaurant info / pure greeting**
   If message is only greeting/thanks/goodbye or asks for hours/location/contact/parking -> `restaurant_info` with specific topic, or {{"topic":"greeting"}} for pure "hello".

4. **Meal availability check**
   - "do you serve breakfast/lunch/dinner?", "is breakfast available?", "can I get lunch?" -> `check_meal_availability` {{ "meal_type": lowercase meal }}
   - "what time is breakfast/lunch?", "when do you serve lunch?" -> `check_meal_availability` {{ "meal_type": lowercase meal }}

5. **Menu & search intents (no allergy mentioned)**
   - **PRIORITY: Combined dietary + food type**: if message contains BOTH a dietary term (vegetarian/vegan/gluten-free/etc.) AND a food type (pasta/pizza/seafood/etc.) -> `filter_dietary_food_type` with both parameters
     Examples: "vegetarian pasta", "gluten-free pizza", "vegan seafood", "vegetarian pasta that's also gluten-free"
   - **Valid food type categories**: "your pasta dishes", "what chicken do you have?", "I want beef", "show me seafood" -> `search_by_food_type` {{ "food_type": TitleCase }}
     Valid categories: Pasta, Beef, Chicken, Seafood, Fish, Pork, Lamb, Veal, Poultry, Shellfish, Salad, Soup, Dessert, Appetizer, Vegan, Vegetarian, Comfort Food, Gourmet, Healthy, Raw
   - **Specific dish names**: "spaghetti carbonara", "chicken tikka masala", "risotto", "gnocchi", "arancini" -> `get_dish_details` {{ "dish_name": raw string }}
   - **Meal time**: "what's for lunch/dinner?" -> `search_by_meal_time`
   - **Course type**: "show appetizers", "any desserts?" -> `search_by_course_type`
   - **Ingredient**: "dishes with truffle", "mushroom dishes" -> `search_menu_by_ingredient`
   - **Dietary filter**: "vegetarian options", "vegan dishes" -> `filter_dietary`
   - **General menu**: "menu", "what's good here?", "what do you have?" -> `search_menu_general` {{ "scope": "menu" or "popular" }}

6. **Default rule — forbid empty arrays**
   If none match but message mentions food/menu -> `search_menu_general` {{ "scope":"menu" }}
   Only when message is neither food-related nor info-seeking -> `restaurant_info` {{ "topic":"greeting" }}
   **You must never output an empty array.**

## Normalization
Map tokens to TitleCase: pasta->Pasta, chicken->Chicken, beef->Beef
Possessives/helpers ("your/our/do you have/I want/show me") do NOT change intent; treat like direct commands.
For allergies: "milk"->"dairy", "peanut"/"peanuts"->"nuts", "shell fish"/"crustacean"->"shellfish"

## Output examples
- "Show me your pasta dishes" -> [{{"tool":"search_by_food_type","parameters":{{"food_type":"Pasta"}}}}]
- "What chicken do you have?" -> [{{"tool":"search_by_food_type","parameters":{{"food_type":"Chicken"}}}}]
- "I want pasta" -> [{{"tool":"search_by_food_type","parameters":{{"food_type":"Pasta"}}}}]
- "Show me risotto" -> [{{"tool":"get_dish_details","parameters":{{"dish_name":"risotto"}}}}]
- "Do you have gnocchi?" -> [{{"tool":"get_dish_details","parameters":{{"dish_name":"gnocchi"}}}}]
- "Show me vegetarian pasta that's also gluten-free" -> [{{"tool":"filter_dietary_food_type","parameters":{{"diet":["Vegetarian","Gluten-Free"],"food_type":"Pasta"}}}}]
- "Do you have vegan pizza?" -> [{{"tool":"filter_dietary_food_type","parameters":{{"diet":["Vegan"],"food_type":"Pizza"}}}}]
- "Show me the menu" -> [{{"tool":"search_menu_general","parameters":{{"scope":"menu","message_context":"Show me the menu"}}}}]
- "What's good here?" -> [{{"tool":"search_menu_general","parameters":{{"scope":"popular","message_context":"What's good here?"}}}}]
- "Which one is most popular?" -> [{{"tool":"search_menu_general","parameters":{{"scope":"popular","message_context":"Which one is most popular?"}}}}]
- "Hello" -> [{{"tool":"restaurant_info","parameters":{{"topic":"greeting"}}}}]
- "I'm allergic to nuts" -> [{{"tool":"update_allergy_add","parameters":{{"allergies":["nuts"]}}}}]
- "Remove dairy" -> [{{"tool":"ask_clarify","parameters":{{"question":"Do you want to remove dairy from your allergy list, or see dairy-free menu items?"}}}}]

Return ONLY the JSON array."""

    return prompt

def execute_tool(tool_data: Dict, menu_items: List[Dict], customer_profile: Optional[Any] = None, restaurant_data: Optional[Dict] = None) -> Dict:
    """Execute a tool with given parameters"""
    tool_name = tool_data.get("tool")
    params = tool_data.get("parameters", {})
    
    logger.info(f"=== EXECUTING TOOL ===")
    logger.info(f"Tool: {tool_name}")
    logger.info(f"Parameters: {params}")
    logger.info(f"Menu items count: {len(menu_items)}")
    
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
                # Check allergen safety even for exact matches
                if is_safe_for_customer(item):
                    return {
                        "tool": tool_name,
                        "found": 1,
                        "match_type": "exact",
                        "items": [{
                            "name": item.get('dish') or item.get('name'),
                            "price": item.get('price'),
                            "description": item.get('description'),
                            "ingredients": item.get('ingredients', []),
                            "allergens": item.get('allergens', [])
                        }]
                    }
        
        # Smart partial matching - ALL search words must be present
        matches = []
        search_words = dish_name.split()
        
        for item in menu_items:
            item_name = (item.get('dish', '') or item.get('name', '')).lower()
            
            # Check if ALL search words are in the dish name
            if all(word in item_name for word in search_words):
                # Also check allergen safety
                if is_safe_for_customer(item):
                    matches.append(item)
        
        # Return results based on matches found
        if len(matches) > 0:
            return {
                "tool": tool_name,
                "found": len(matches),
                "match_type": "partial",
                "search_term": dish_name,
                "items": [
                    {
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "description": item.get('description'),
                        "ingredients": item.get('ingredients', []),
                        "allergens": item.get('allergens', [])
                    } for item in matches
                ]
            }
        
        # No matches found - provide alternative suggestions
        alternatives = []
        
        # Try to find similar items based on food type or category
        if "pizza" in dish_name:
            # Look for pizza items
            for item in menu_items:
                item_name = (item.get('dish', '') or item.get('name', '')).lower()
                if "pizza" in item_name and is_safe_for_customer(item):
                    alternatives.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "description": item.get('description', ''),
                        "ingredients": item.get('ingredients', []),
                        "allergens": item.get('allergens', [])
                    })
                    if len(alternatives) >= 3:  # Limit to 3 suggestions
                        break
        elif "pasta" in dish_name:
            # Look for pasta items
            for item in menu_items:
                item_name = (item.get('dish', '') or item.get('name', '')).lower()
                if any(pasta_type in item_name for pasta_type in ["pasta", "spaghetti", "penne", "linguine", "fettuccine", "ravioli", "lasagna"]):
                    if is_safe_for_customer(item):
                        alternatives.append({
                            "name": item.get('dish') or item.get('name'),
                            "price": item.get('price'),
                            "description": item.get('description', ''),
                            "ingredients": item.get('ingredients', []),
                            "allergens": item.get('allergens', [])
                        })
                        if len(alternatives) >= 3:
                            break
        
        return {
            "tool": tool_name, 
            "found": 0,
            "match_type": "none",
            "search_term": dish_name,
            "items": [],
            "alternatives": alternatives[:3] if alternatives else []
        }
    
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
        
        # CRITICAL: Check if food_type parameter is missing
        if not food_type:
            logger.error("search_by_food_type called without food_type parameter!")
            return {
                "tool": tool_name,
                "error": "Missing required parameter: food_type",
                "found": 0,
                "items": []
            }
        
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
            dish_name_lower = (item.get('dish') or item.get('name', '') or '').lower()
            
            # Check if food_type matches any category
            if (
                food_type in categories_lower
                or food_type == single_category_lower
            ):
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
        
        # GENERAL FALLBACK: If no results found by category matching, try item name search
        if len(results) == 0:
            logger.warning(f"[FALLBACK] No category matches found for '{food_type}', trying general item name search...")
            food_type_lower = food_type.lower()
            for item in menu_items:
                dish_name = (item.get('dish') or item.get('name', '') or '').lower()
                # General item name matching - works for any food type
                if food_type_lower in dish_name:
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
            logger.warning(f"[FALLBACK] General item name search found {len(results)} items for '{food_type}'")
        
        return {
            "tool": tool_name,
            "food_type": params.get("food_type"),
            "found": len(results),
            "items": results,
            "pre_filtered": customer_allergies is not None and len(customer_allergies) > 0
        }
    
    elif tool_name in ["filter_vegetarian", "filter_vegan", "filter_gluten_free", "filter_nut_free", "filter_dairy_free", "filter_shellfish_free", "filter_fish_free", "filter_dietary_food_type"]:
        # For filter_dietary_food_type, we need to get the diet from parameters
        if tool_name == "filter_dietary_food_type":
            diet_list = params.get("diet", []) or []
            filter_type = diet_list[0].lower().replace("_", "-") if diet_list else "vegetarian"
            logger.info(f"filter_dietary_food_type: Filtering by diet='{filter_type}' from diet_list={diet_list}")
        else:
            filter_type = tool_name.replace("filter_", "").replace("_", "-")
        results = []
        
        logger.info(f"Dietary filter: tool={tool_name}, filter_type={filter_type}, menu_items={len(menu_items)}")
        
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
            elif filter_type == "fish-free":
                # Check for fish in allergens
                allergens = [a.lower() for a in item.get('allergens', [])]
                if "fish" not in allergens:
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
        
        # If combined dietary + food type filter was requested, post-filter results by food type
        if tool_name == "filter_dietary_food_type":
            diet_list = params.get("diet", []) or []
            food_type = (params.get("food_type", "") or "").lower()
            filtered = []
            
            logger.info(f"filter_dietary_food_type: Found {len(results)} dietary matches, now filtering by food_type='{food_type}'")
            
            # We need to re-check against the original menu items for food type matching
            # because the filtered results don't have the full category information
            for item in results:
                # Find the original menu item to get full category information
                item_name = item.get('name', '').lower()
                original_item = None
                for menu_item in menu_items:
                    menu_name = (menu_item.get('dish') or menu_item.get('name', '')).lower()
                    if menu_name == item_name:
                        original_item = menu_item
                        break
                
                logger.info(f"filter_dietary_food_type: Processing item '{item_name}', found original: {original_item is not None}")
                
                if original_item:
                    # Check food type against original item
                    name_lower = item_name
                    cats = [c.lower() for c in (original_item.get('restaurant_categories') or [])]
                    single = (original_item.get('restaurant_category') or '').lower()
                    is_risotto = 'risotto' in name_lower or 'risotto' in cats or single == 'risotto'
                    is_pasta_like = any(kw in name_lower for kw in [
                        'spaghetti','penne','linguine','fettuccine','ravioli','lasagna','gnocchi','tagliatelle','pappardelle'
                    ])
                    match = (
                        (food_type in cats or food_type == single)
                        or (food_type == 'pasta' and is_pasta_like)
                        or (food_type == 'risotto' and is_risotto)
                    )
                    
                    logger.info(f"filter_dietary_food_type: Item '{item_name}' - cats: {cats}, single: {single}, is_pasta_like: {is_pasta_like}, is_risotto: {is_risotto}, match: {match}")
                    
                    if match:
                        if food_type == 'pasta' and is_risotto:
                            logger.info(f"filter_dietary_food_type: Skipping risotto item '{item_name}' for pasta query")
                            continue
                        logger.info(f"filter_dietary_food_type: Adding item '{item_name}' to filtered results")
                        filtered.append(item)
                else:
                    # Fallback: if we can't find original item, use name-based matching
                    name_lower = item_name
                    is_risotto = 'risotto' in name_lower
                    is_pasta_like = any(kw in name_lower for kw in [
                        'spaghetti','penne','linguine','fettuccine','ravioli','lasagna','gnocchi','tagliatelle','pappardelle'
                    ])
                    match = (
                        (food_type == 'pasta' and is_pasta_like)
                        or (food_type == 'risotto' and is_risotto)
                        or (food_type in name_lower)
                    )
                    if match:
                        if food_type == 'pasta' and is_risotto:
                            continue
                        filtered.append(item)
            
            results = filtered
            logger.info(f"filter_dietary_food_type: After food_type filtering, found {len(results)} items")

        return {
            "tool": tool_name,
            "filter": filter_type,
            "found": len(results),
            "items": results
        }
    
    elif tool_name in ["update_allergy_add", "update_allergy_remove"]:
        # These are handled separately in the main function
        return {"tool": tool_name, "action": "pending", "allergies": params.get("allergies", [])}
    
    elif tool_name == "ask_clarify":
        # Handle ambiguous requests that need clarification
        question = params.get("question", "Could you clarify what you mean?")
        return {
            "tool": tool_name,
            "response_type": "clarification_needed",
            "question": question,
            "do_not_suggest_food": True
        }
    
    elif tool_name == "no_food_response":
        # Handle MIA backend hallucinating this tool from v6/v7 usage
        # Treat it as no_tool_needed to prevent fallback
        logger.warning("MIA selected non-existent 'no_food_response' tool - treating as no_tool_needed")
        return {"info": "No execution needed", "tool": tool_name}
    
    elif tool_name == "search_menu_general":
        # New catch-all tool for general menu requests
        scope = params.get("scope", "menu")
        results = []
        
        if scope == "menu":
            # Return a diverse selection from the menu
            results = menu_items[:20]  # First 20 items
        elif scope == "popular":
            # Popularity selection with optional course filtering (e.g., desserts only)
            course_type = (params.get("course_type", "") or "").lower()
            candidates = menu_items

            # Enhanced context inference: if no course_type provided, try to infer from message context
            if not course_type:
                # Look for context clues in the message that might indicate a specific course type
                # This is a simple heuristic - in a real implementation, you'd pass conversation history
                message_context = params.get("message_context", "").lower()
                if any(word in message_context for word in ["dessert", "sweet", "cake", "ice cream", "tiramisu", "cheesecake"]):
                    course_type = "dessert"
                elif any(word in message_context for word in ["appetizer", "starter", "app", "begin"]):
                    course_type = "appetizer"
                elif any(word in message_context for word in ["main", "entree", "dinner", "lunch"]):
                    course_type = "main"

            # If course_type is provided (e.g., 'dessert', 'starter', 'main'), filter candidates first
            if course_type:
                candidates = [it for it in candidates if (it.get('subcategory', '') or '').lower() == course_type]

            # Prefer explicit popularity signals when available, else use price as proxy
            def _popularity_key(it):
                explicit = it.get('popularity')
                try:
                    price_val = float(str(it.get('price', '0')).replace('$', '').strip() or 0)
                except Exception:
                    price_val = 0.0
                # explicit popularity descending (None -> -1), then price descending
                return (explicit if isinstance(explicit, (int, float)) else -1, price_val)

            sorted_items = sorted(candidates, key=_popularity_key, reverse=True)

            # If filtering produced no candidates, gracefully fallback to general popular
            if course_type and not sorted_items:
                sorted_items = sorted(menu_items, key=_popularity_key, reverse=True)

            results = sorted_items[:10]
        elif scope == "recommendations":
            # Return chef recommendations (variety of items)
            # Get 2-3 from each category
            by_category = {}
            for item in menu_items:
                cat = item.get('subcategory', 'Other')
                if cat not in by_category:
                    by_category[cat] = []
                by_category[cat].append(item)
            
            for cat, items in by_category.items():
                results.extend(items[:2])
                if len(results) >= 10:
                    break
        elif scope == "specials":
            # Return daily specials (for now, just return some featured items)
            results = [item for item in menu_items if 'special' in (item.get('name', '') + item.get('dish', '')).lower()][:5]
            if not results:
                results = menu_items[5:10]  # Default to some items
        
        # Filter for customer safety
        safe_results = []
        for item in results:
            if is_safe_for_customer(item):
                safe_results.append(item)
        
        return {
            "tool": tool_name,
            "scope": scope,
            "found": len(safe_results),
            "items": safe_results,
            "category": "GENERAL MENU"
        }
    
    elif tool_name == "check_meal_availability":
        # Check if restaurant serves breakfast/lunch/dinner
        meal_type = params.get("meal_type", "").lower()
        
        # Count items by category
        meal_counts = {
            "breakfast": 0,
            "lunch": 0, 
            "dinner": 0,
            "brunch": 0
        }
        
        for item in menu_items:
            category = (item.get('category', '') or '').lower()
            if category in meal_counts:
                meal_counts[category] += 1
        
        # Determine availability
        available = meal_counts.get(meal_type, 0) > 0
        
        # Get service times and custom messages if available
        service_times = {}
        custom_message = None
        if restaurant_data:
            service_times = restaurant_data.get('service_times', {})
            custom_messages = restaurant_data.get('custom_messages', {})
            
            # Check service_times configuration
            meal_config = service_times.get(meal_type, {})
            if isinstance(meal_config, dict) and 'available' in meal_config:
                # Override availability based on configuration
                available = meal_config.get('available', available)
            
            # Get custom message for unavailable meals
            if not available:
                if meal_type == "breakfast":
                    custom_message = custom_messages.get('no_breakfast_message')
                elif meal_type == "lunch":
                    custom_message = custom_messages.get('no_lunch_message')
        
        return {
            "tool": tool_name,
            "meal_type": meal_type,
            "available": available,
            "item_count": meal_counts.get(meal_type, 0),
            "all_meal_counts": meal_counts,
            "custom_message": custom_message,
            "service_times": service_times.get(meal_type, {})
        }
    
    else:
        return {"error": f"Unknown tool: {tool_name}"}

def execute_non_food_tool(tool_name: str, params: Dict, customer_profile: Optional[Any] = None, restaurant_data: Dict = None) -> Dict:
    """Execute non-food related tools that do not need menu context"""
    
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
        # Handle both old parameter name (info_type) and new (topic) for compatibility
        topic = params.get("topic", params.get("info_type", "general"))
        
        # Use actual restaurant data if available
        if restaurant_data:
            restaurant_name = restaurant_data.get('business_name', 'our restaurant')
            hours = restaurant_data.get('opening_hours', 'Please check our website for current hours')
            address = restaurant_data.get('address', '')
            phone = restaurant_data.get('contact_info', {}).get('phone', '')
            email = restaurant_data.get('contact_info', {}).get('email', '')
            description = restaurant_data.get('business_description', f'{restaurant_name} is here to serve you')
            
            # Get greeting from chat settings
            chat_settings = restaurant_data.get('chat_settings', {})
            custom_messages = chat_settings.get('custom_messages', {})
            greeting = custom_messages.get('greeting', f"Welcome to {restaurant_name}!")
            
            info_map = {
                "hours": hours,
                "location": address if address else "Location information not available",
                "contact": f"Phone: {phone}, Email: {email}" if phone or email else "Contact information not available",
                "general": description,
                "greeting": greeting
            }
        else:
            # Fallback to generic responses
            info_map = {
                "hours": "Please check our website for current hours",
                "location": "Location information not available",
                "contact": "Contact information not available", 
                "general": "Welcome to our restaurant",
                "greeting": "Welcome!"
            }
        
        return {
            "tool": tool_name,
            "info_type": topic,  # Keep for backward compatibility
            "topic": topic,
            "info": info_map.get(topic, info_map["general"]),
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
    
    elif tool_name == "ask_clarify":
        # Handle clarification requests
        question = params.get("question", "Could you clarify what you mean?")
        return {
            "tool": tool_name,
            "response_type": "clarification_needed", 
            "question": question,
            "do_not_suggest_food": True,
            "has_dietary_restrictions": has_restrictions,
            "restrictions": restriction_info
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
    logger.info(f"Tools to execute: {[t.get('tool') for t in tools]}")
    
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
                elif filter_type == "fish-free":
                    allergens = [a.lower() for a in item.get('allergens', [])]
                    if "fish" not in allergens:
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
    
    # Debug log to check if something is wrong
    if all(r['found'] == 0 for r in final_results) and len(final_results) > 1:
        logger.warning(f"WARNING: All {len(final_results)} tools returned 0 items! This might be a bug.")
        logger.warning(f"Menu items passed: {len(menu_items)}, Tools: {[r['tool'] for r in final_results]}")
    
    return final_results

def build_phase2_prompt(message: str, tool_results: List[Dict], restaurant_name: str, 
                       customer_profile: Any, context_type: str, context_data: Dict,
                       chat_history: List[Dict] = None) -> str:
    """Build Phase 2 prompt for final response generation"""
    
    # Check if ask_clarify tool was executed
    ask_clarify_executed = any(
        result.get("tool") == "ask_clarify"
        for result in tool_results
    )
    
    # Check if any non-food tools were executed
    non_food_tools_executed = any(
        result.get("tool") in ["explain_reasoning", "handle_misunderstanding", "restaurant_info", "change_preference"]
        and result.get("do_not_suggest_food", False)
        for result in tool_results
    )
    
    # Special handling for ask_clarify
    if ask_clarify_executed:
        # Build specialized clarification prompt
        clarify_result = next(r for r in tool_results if r.get("tool") == "ask_clarify")
        clarify_question = clarify_result.get("question", "Could you clarify what you mean?")
        
        prompt = f"""You are a Clarifier assistant for {restaurant_name}.

Your ONLY job is to ask a clarifying question when the customer intent is ambiguous.

CONTEXT:
Customer said: "{message}"

AMBIGUITY DETECTED:
The system needs clarification about what the customer wants.

YOUR TASK:
Ask ONE short, specific clarifying question to understand their intent better.

RESPONSE FORMAT:
- Ask only ONE question
- Keep it under 20 words
- Use quick reply buttons format: [Option 1] [Option 2]
- Be friendly and natural

EXAMPLES:
- "Do you want to [remove dairy from your allergies] or [see dairy-free dishes]?"
- "Are you looking for [pasta dishes] or just asking about [specific pasta types]?"
- "Would you like me to [update your allergies] or [show you safe menu items]?"

SUGGESTED QUESTION (you can rephrase):
{clarify_question}

Your clarifying question:"""
        
        return prompt
    
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
    elif context_type == "intersection_zero_with_options":
        prompt = f"""You are Maria, a helpful and understanding server at {restaurant_name}.

The customer is looking for items with multiple criteria but we do not have anything that matches ALL their requirements.

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
    # Special handling for intersection_zero_with_options - do not show any food items
    if context_type == "intersection_zero_with_options":
        prompt += "\nNO ITEMS MATCH ALL CRITERIA - See guidelines below for how to respond\n"
    else:
        for result in tool_results:
            if result.get("tool") == "no_tool_needed":
                continue
            elif result.get("tool") == "check_meal_availability":
                meal_type = result.get("meal_type", "meal")
                available = result.get("available", False)
                prompt += f"\nMEAL AVAILABILITY CHECK:\n"
                if available:
                    prompt += f"✓ Yes, we serve {meal_type}. We have {result.get('item_count', 0)} {meal_type} items on our menu.\n"
                else:
                    # Use custom message if available
                    custom_message = result.get("custom_message")
                    if custom_message:
                        prompt += f"CUSTOM RESPONSE: {custom_message}\n"
                    else:
                        prompt += f"✗ We do not serve {meal_type}.\n"
                    
                    # Add context about what meals are available
                    meal_counts = result.get("all_meal_counts", {})
                    available_meals = [meal for meal, count in meal_counts.items() if count > 0]
                    if available_meals and not available and not custom_message:
                        prompt += f"We specialize in: {', '.join(available_meals)}\n"
            elif result.get("tool") == "get_dish_details":
                if result.get("found"):
                    items = result.get("items", [])
                    if items:
                        prompt += f"\nDISH DETAILS:\n"
                        
                        # If spelling was corrected, note it
                        if result.get("corrected"):
                            prompt += f"(Found match for '{result.get('original_query')}')\n"
                        
                        for dish in items:
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
                        
                    items = result.get("items", [])
                    for item in items:
                        name = item.get('name', 'Unknown')
                        price = item.get('price', 'Price not available')
                        prompt += f"- {name} {price}\n"
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
                    # Handle empty filter results with clearer messaging
                    filter_type = result.get('filter', '')
                    food_type = result.get('food_type', '')
                    
                    if filter_type:
                        prompt += f"\n{filter_type.upper()} SEARCH RESULTS:\n"
                        prompt += f"❌ We do not have any {filter_type.replace('_', ' ')} options on our menu.\n"
                    elif food_type:
                        prompt += f"\n{food_type.upper()} SEARCH RESULTS:\n"
                        prompt += f"❌ We do not have {food_type} on our menu.\n"
                    else:
                        prompt += f"\n{result.get('category', 'SEARCH')} RESULTS:\n"
                        prompt += f"❌ No items found matching your request.\n"
    
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
   - They seem confused or there is a misunderstanding - clarify what you meant
   - Be patient and helpful in clearing up any confusion
"""
            elif result.get("tool") == "ask_clarify":
                question = result.get("question", "Could you clarify what you mean?")
                prompt += f"""
   - The request was ambiguous and needs clarification
   - Ask this specific question: "{question}"
   - Do not suggest food items until the clarification is received
"""
            elif result.get("tool") == "restaurant_info":
                prompt += """
   - They want information about the restaurant - provide relevant details
   - This might include hours, policies, location, or general information
"""
            elif result.get("tool") == "change_preference":
                prompt += """
   - They want to change their preferences or restrictions
   - Acknowledge the change and confirm you will remember it
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
3. ALLERGEN FACTS - IMPORTANT:
   - Fish (salmon, tuna, sea bass) are NOT shellfish
   - Shellfish includes: shrimp, crab, lobster, oysters, clams, mussels, scallops
   - Common allergens are SEPARATE categories: Dairy, Eggs, Nuts, Soy, Sesame, Gluten, Shellfish, Fish
   - NEVER say one allergen "is also" another type (e.g., do not say "soy is a shellfish allergen")
4. A dish is SAFE if it does not contain the customer allergens.
   A dish is UNSAFE if the allergen is explicitly listed.
   A dish is UNKNOWN if not listed in menu results - politely say it is not available.
5. If allergen might reasonably appear in an ingredient but is not listed, say:
   "Based on the provided menu data, this dish does not list [allergen], but I recommend double-checking with staff for your safety."
6. Responses must be concise (2-3 sentences max).
   - Use exact dish names and prices.
   - Use short lists for multiple dishes.
7. Always continue applying allergy/dietary filters from Phase 1.
8. Stay natural, warm, and professional - but never compromise on menu accuracy or safety.

Customer is allergic to: {', '.join(customer_allergies) if customer_allergies else 'nothing specified'}
"""
    elif context_type == "intersection_zero_with_options":
        # Extract the original counts before intersection
        original_counts = context_data.get("original_counts", {})
        
        prompt += f"""
SPECIAL HANDLING - NO ITEMS MATCH ALL CRITERIA:
You searched for items with multiple criteria, but nothing matches ALL requirements together.

ORIGINAL SEARCH RESULTS (before combining):
"""
        # Show what each individual filter would have found
        for i, result in enumerate(tool_results):
            tool_name = result.get("tool", "")
            original_count = original_counts.get(i, 0)
            if original_count > 0:
                if tool_name == "search_by_food_type":
                    prompt += f"- {result.get('food_type', 'Food type')}: {original_count} items available\n"
                elif tool_name.startswith("filter_"):
                    filter_type = tool_name.replace("filter_", "").replace("_", " ")
                    prompt += f"- {filter_type.title()}: {original_count} items available\n"
                elif tool_name == "search_by_meal_time":
                    prompt += f"- {result.get('meal_time', 'Meal time')}: {original_count} items available\n"
                elif tool_name == "search_by_course_type":
                    prompt += f"- {result.get('course_type', 'Course type')}: {original_count} items available\n"

        prompt += """
HOW TO RESPOND:
1. Be understanding and acknowledge their specific request
2. Explain that while we do not have items matching ALL criteria, we have options for each individual requirement
3. Offer to help them choose based on what is most important to them
4. Keep the tone helpful and solution-focused

Example response structure:
\"I understand you are looking for [specific combination]. While we do not have any dishes that are both [X] AND [Y], I can offer you some great options:
- For [X], we have [specific dishes]  
- For [Y], we have [other specific dishes]
Which preference is most important to you today, or would you like me to describe some of these options?\"

IMPORTANT: Be specific about what combination was not available, and be clear about what IS available.
"""
    else:
        # Check if any search returned 0 items
        has_zero_results = any(
            result.get("found") == 0 
            for result in tool_results 
            if isinstance(result.get("found"), int)
        )
        
        # Check if this is due to intersection of multiple filters
        search_filter_tools_used = []
        for result in tool_results:
            tool_name = result.get("tool", "")
            if tool_name in ["search_by_food_type", "search_by_meal_time", "search_by_course_type", 
                           "filter_vegetarian", "filter_vegan", "filter_gluten_free", 
                           "filter_nut_free", "filter_dairy_free", "filter_shellfish_free", "filter_fish_free"]:
                search_filter_tools_used.append(tool_name)
        
        is_intersection_zero = len(search_filter_tools_used) > 1 and has_zero_results
        
        if has_zero_results:
            if is_intersection_zero:
                # Multiple filters resulted in 0 items - be specific about the combination
                prompt += """
STRICT RULES - NO ITEMS MATCH ALL YOUR CRITERIA:
- Multiple filters were applied and NO items match ALL criteria
- Be SPECIFIC about what combination wasn't found
- IMPORTANT: We likely have items that match SOME criteria, just not ALL

How to respond:
1. Say specifically: "We do not have any [X] that is also [Y] and [Z]"
2. Then offer items that match SOME criteria:
   - "However, we do have [X] options that are [Y]" 
   - "And we have [Z] dishes that are [X]"
3. Ask which they'd prefer or if they'd like to adjust criteria

Example responses:
- "We do not have any pasta dishes that are both gluten-free AND dairy-free. However, we have gluten-free pasta options like Mushroom Risotto, and dairy-free pasta like Penne Arrabbiata. Which would you prefer?"
- "We do not have any appetizers that are vegan. However, we have vegetarian appetizers like Caprese Skewers, or vegan main dishes like Buddha Bowl. What sounds good?"
"""
                # Add tool information to help craft specific response
                filter_descriptions = []
                for result in tool_results:
                    tool = result.get("tool", "")
                    if tool == "search_by_food_type":
                        filter_descriptions.append(f"{result.get('food_type', '')} dishes")
                    elif tool == "filter_vegetarian":
                        filter_descriptions.append("vegetarian")
                    elif tool == "filter_vegan":
                        filter_descriptions.append("vegan")
                    elif tool == "filter_gluten_free":
                        filter_descriptions.append("gluten-free")
                    elif tool == "filter_dairy_free":
                        filter_descriptions.append("dairy-free")
                    elif tool == "filter_nut_free":
                        filter_descriptions.append("nut-free")
                    elif tool == "filter_shellfish_free":
                        filter_descriptions.append("shellfish-free")
                    elif tool == "filter_fish_free":
                        filter_descriptions.append("fish-free")
                
                if filter_descriptions:
                    prompt += f"\nFilters applied: {' AND '.join(filter_descriptions)}\n"
                
                # Add information about items that match SOME criteria
                partial_matches_info = []
                for result in tool_results:
                    if result.get("found", 0) > 0:
                        tool = result.get("tool", "")
                        if tool == "search_by_food_type":
                            partial_matches_info.append(f"- We have {result.get('found')} {result.get('food_type', '')} dishes")
                        elif tool == "filter_vegetarian":
                            partial_matches_info.append(f"- We have {result.get('found')} vegetarian options")
                        elif tool == "filter_vegan":
                            partial_matches_info.append(f"- We have {result.get('found')} vegan options")
                        elif tool == "filter_gluten_free":
                            partial_matches_info.append(f"- We have {result.get('found')} gluten-free items")
                        elif tool == "filter_dairy_free":
                            partial_matches_info.append(f"- We have {result.get('found')} dairy-free items")
                        elif tool == "filter_nut_free":
                            partial_matches_info.append(f"- We have {result.get('found')} nut-free items")
                
                if partial_matches_info:
                    prompt += "\nWhat we DO have:\n" + "\n".join(partial_matches_info) + "\n"
            else:
                # Single search returned 0 or category doesn't exist
                prompt += """
STRICT RULES - WE FOUND 0 ITEMS:
- Customer asked for something we DO NOT have
- You MUST first say: "We do not have [X] on our menu"
- NEVER say "We have X" when X wasn't found
- NEVER try to make other dishes sound like what they asked for (e.g., do not call carpaccio a "burger")
- After acknowledging what we DO NOT have, offer: "Would you like me to suggest some alternatives?"
- For breakfast/lunch: Check custom messages or use default unavailable message
- Be honest, then helpful

Example responses:
- "We do not have pizza on our menu. Would you like me to suggest some Italian pasta dishes instead?"
- "We do not have burgers. Would you like to see our other meat dishes?"
- "We do not serve breakfast. Would you like to see our dinner menu?"
"""
        else:
            # Normal guidelines when items were found
            prompt += """
RESPONSE GUIDELINES:
- Use EXACT dish names and prices from the menu data above
- Keep response concise (2-3 sentences max)
- NEVER say "Hello" if already greeted
- If listing multiple items, include prices for each
- Be natural and helpful
- NEVER invent or suggest dishes that aren't in the search results above
"""
    
    prompt += "\nRespond naturally:"
    
    return prompt

def generate_response_internal_tools_v5(req: Any, db: Session) -> Any:
    """2-Phase flow: Tool selection with params -> Response generation"""
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
            logger.warning("MIA returned null response")
            selection_text = ""
        
        selection_text = selection_text.strip()
        
        # DEBUG: Log raw response
        logger.info(f"=== PHASE 1 RAW RESPONSE ===")
        logger.info(f"Message: '{req.message}'")
        logger.info(f"Raw selection text: {repr(selection_text[:500])}")
        
        # Check for common LLM response issues
        if selection_text.startswith("```json"):
            logger.warning("LLM returned markdown code block, extracting JSON")
            selection_text = selection_text.replace("```json", "").replace("```", "").strip()
        
        # Check if LLM added explanation text
        if selection_text and not selection_text.strip().startswith("["):
            logger.warning("LLM may have added explanation text before JSON")
            # Try to find the JSON array
            json_start = selection_text.find("[")
            if json_start != -1:
                selection_text = selection_text[json_start:]
                logger.info(f"Extracted JSON from position {json_start}")
        
        try:
            selected_tools = json.loads(selection_text)
            if not isinstance(selected_tools, list):
                logger.warning(f"Response not a list: {type(selected_tools)}")
                selected_tools = [{"tool": "no_tool_needed"}]
            else:
                # Ensure all elements are dictionaries and remove null entries
                fixed_tools = []
                for i, tool in enumerate(selected_tools):
                    if tool is None:
                        logger.warning(f"Tool {i} is null, skipping")
                        continue
                    elif isinstance(tool, dict):
                        # Check if tool has required fields
                        if not tool.get("tool"):
                            logger.warning(f"Tool {i} missing 'tool' field: {tool}")
                            if "parameters" in tool and not tool.get("tool"):
                                # Skip tools with only parameters but no tool name
                                continue
                        fixed_tools.append(tool)
                    elif isinstance(tool, str):
                        # Convert string to proper format
                        logger.warning(f"Tool {i} returned as string: {tool}, converting to dict")
                        fixed_tools.append({"tool": tool, "parameters": {}})
                    else:
                        logger.error(f"Tool {i} unknown format: {type(tool)} - {tool}")
                        
                # CRITICAL FIX: Check if fixed_tools is empty list (not just falsy)
                if not fixed_tools or len(fixed_tools) == 0:
                    logger.warning("Empty tools array detected, defaulting to search_menu_general")
                    selected_tools = [{"tool": "search_menu_general", "parameters": {"scope": "menu"}}]
                else:
                    selected_tools = fixed_tools
                
                # DEBUG: Log parsed tools
                logger.info(f"Parsed {len(selected_tools)} tools from {len(selected_tools) + (len(selected_tools) - len(fixed_tools))} original")
                
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            logger.error(f"Failed text: {selection_text[:200]}")
            selected_tools = [{"tool": "no_tool_needed"}]
        except Exception as e:
            logger.error(f"Unexpected error parsing tools: {e}")
            logger.error(f"Selection text: {selection_text[:200]}")
            selected_tools = [{"tool": "no_tool_needed"}]
        
        logger.info(f"Final selected tools: {json.dumps(selected_tools, indent=2)}")
        
        # Handle simple flow (no tools needed or no_food_response)
        if len(selected_tools) == 1 and selected_tools[0].get("tool") in ["no_tool_needed", "no_food_response"]:
            # Check message type
            goodbye_keywords = ["goodbye", "bye", "see you", "later", "take care", "have a good"]
            greeting_keywords = ["hello", "hi", "hey", "good morning", "good afternoon", "good evening"]
            thanks_keywords = ["thank", "thanks", "appreciate"]
            
            message_lower = req.message.lower()
            is_goodbye = any(keyword in message_lower for keyword in goodbye_keywords)
            is_greeting = any(keyword in message_lower for keyword in greeting_keywords)
            is_thanks = any(keyword in message_lower for keyword in thanks_keywords)
            
            # Always exclude menu for no_tool_needed - if food info is needed, AI should use search tools
            exclude_menu = True
            
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
            
            # Since exclude_menu is always True for no_tool_needed, we don't need menu
            simple_prompt += f"""Current message: "{req.message}"

CRITICAL INSTRUCTIONS:
- {"This is a goodbye/farewell message" if is_goodbye else ""}
- {"This is a greeting" if is_greeting else ""}
- {"Customer is thanking you" if is_thanks else ""}
- Be warm and friendly
- {"Thank them for their visit/interest" if is_goodbye else ""}
- ABSOLUTELY NO food suggestions, menu items, dishes, or prices
- DO NOT mention any food whatsoever
- DO NOT ask about food preferences or dietary needs
- Keep it brief (1-2 sentences)
- Focus only on the greeting/thanks/goodbye itself

Respond:"""
            menu_summary = ""  # No menu for no_tool_needed
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={"message": simple_prompt, "max_tokens": 200},
                timeout=30
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "")
                
                # Always add debug info
                tool_name = selected_tools[0].get("tool")
                debug_info = {
                    "flow": f"simple ({tool_name})",
                    "is_goodbye": is_goodbye,
                    "is_greeting": is_greeting,
                    "is_thanks": is_thanks,
                    "menu_excluded": True,  # Always true for no_tool_needed
                    "menu_summary_length": 0,
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
                    # Normalize allergies to lowercase for consistency
                    allergies = [str(a).lower().strip() for a in allergies if a]
                    
                    if tool_data["tool"] == "update_allergy_add":
                        # Add allergies to profile
                        if customer_profile:
                            existing_allergies = set(str(a).lower().strip() for a in (customer_profile.allergies or []) if a)
                            existing_allergies.update(allergies)
                            customer_profile.allergies = list(existing_allergies)
                            db.commit()
                            logger.info(f"Added allergies to profile: {allergies}. Profile now has: {customer_profile.allergies}")
                    else:
                        # Remove allergies from profile
                        if customer_profile:
                            existing_allergies = set(str(a).lower().strip() for a in (customer_profile.allergies or []) if a)
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
        NON_FOOD_TOOLS = ["explain_reasoning", "handle_misunderstanding", "restaurant_info", "change_preference", "no_food_response", "ask_clarify"]
        
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
                             "filter_gluten_free", "filter_nut_free", "filter_dairy_free", "filter_shellfish_free", "filter_fish_free"]:
                search_filter_tools.append(tool_data)
            elif tool_name in NON_FOOD_TOOLS:
                non_food_tools.append(tool_data)
            elif tool_name == "check_meal_availability":
                # This tool needs menu data but is not a search/filter tool
                other_tools.append(tool_data)
            else:
                other_tools.append(tool_data)
        
        # Execute non-food tools first (they don't need menu data)
        for tool_data in non_food_tools:
            tool_name = tool_data.get("tool")
            params = tool_data.get("parameters", {})
            result = execute_non_food_tool(tool_name, params, customer_profile, restaurant_data)
            tool_results.append(result)
            logger.info(f"Non-food tool {tool_name} executed")
        
        # Execute search/filter tools in single pass for performance
        if search_filter_tools:
            search_results = execute_tools_single_pass(search_filter_tools, menu_items, customer_profile)
            tool_results.extend(search_results)
        
        # Execute other tools individually (get_dish_details, no_tool_needed, etc)
        for tool_data in other_tools:
            result = execute_tool(tool_data, menu_items, customer_profile, restaurant_data)
            tool_results.append(result)
            logger.info(f"Tool {tool_data.get('tool')} returned: found={result.get('found', 'N/A')}")
        
        # Check if all searches returned no results (except allergen filters)
        all_empty = True
        has_allergen_filter = False
        
        for i, tool_data in enumerate(selected_tools):
            tool_name = tool_data.get("tool")
            result = tool_results[i]
            
            # Check if this is an allergen filter
            if tool_name in ["filter_vegetarian", "filter_vegan", "filter_gluten_free", "filter_nut_free", "filter_dairy_free", "filter_shellfish_free", "filter_fish_free"]:
                has_allergen_filter = True
            
            # Check if this search returned results
            if result.get("found", 0) > 0 or result.get("info") == "No execution needed":
                all_empty = False
                break
        
        # NO FALLBACK: Always use tool_flow even with 0 results
        # This prevents hallucinations and ensures honest responses
        logger.info(f"All searches empty: {all_empty}, proceeding with tool_flow for honest response")
        
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
                
                # Store original counts before intersection
                original_counts = {}
                for idx in search_filter_indices:
                    result = tool_results[idx]
                    items_key = "items" if "items" in result else "results"
                    original_counts[idx] = {
                        "tool": result.get("tool"),
                        "count": len(result.get(items_key, [])),
                        "items": result.get(items_key, [])[:5]  # Store first 5 items as examples
                    }
                
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
                    
                    # If intersection resulted in 0 items, store original info for context
                    if len(filtered_items) == 0 and len(original_items) > 0:
                        result["original_found"] = len(original_items)
                        result["had_results_before_intersection"] = True
                    
                    logger.info(f"Tool {result.get('tool')}: filtered from {len(original_items)} to {len(filtered_items)} items")
        
        # Check if intersection resulted in 0 items but individual tools had results
        intersection_zero_with_options = False
        if len(search_filter_indices) > 1:
            all_zero = all(tool_results[idx].get("found", 0) == 0 for idx in search_filter_indices)
            had_results_before = any(tool_results[idx].get("had_results_before_intersection", False) for idx in search_filter_indices)
            intersection_zero_with_options = all_zero and had_results_before
            
            if intersection_zero_with_options:
                # Override context type for this special case
                context_type = "intersection_zero_with_options"
                context_data["original_counts"] = original_counts
        
        # Check if ask_clarify tool was used - override context type
        ask_clarify_used = any(result.get("tool") == "ask_clarify" for result in tool_results)
        if ask_clarify_used:
            context_type = "ask_clarify"
            logger.info("ask_clarify tool detected - using specialized context")
        
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
                "phase1_tools_selected": [{"tool": t.get("tool"), "parameters": t.get("parameters", {})} for t in selected_tools],
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