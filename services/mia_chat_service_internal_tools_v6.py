"""
MIA Chat Service V6 - Internal Tools Version with Improved Non-Food Response Handling
Key improvements:
- Emphasizes current message intent over conversation history
- New no_food_response tool for greetings, goodbyes, thanks
- Clean separation between food and non-food contexts
"""

import json
import time
import logging
import requests
from typing import Dict, Any, List, Optional, Tuple
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse
from datetime import datetime, timedelta, timezone
import os
from services.response_validator_universal import validate_response

logger = logging.getLogger(__name__)

# MIA backend URL from environment or default
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "http://localhost:8001")

def create_menu_summary(menu_items: List[Dict]) -> str:
    """Create a compressed menu summary with key details"""
    if not menu_items:
        return "No menu items available"
    
    summary_parts = []
    
    # Group items by category
    by_category = {}
    for item in menu_items[:30]:  # Limit to prevent token overflow
        category = item.get('category', 'Other')
        if category not in by_category:
            by_category[category] = []
        
        # Extract essential info
        name = item.get('dish') or item.get('name', 'Unknown')
        price = item.get('price', 0)
        dietary_tags = []
        if item.get('is_vegetarian'): dietary_tags.append('veg')
        if item.get('is_vegan'): dietary_tags.append('vegan')
        if item.get('is_gluten_free'): dietary_tags.append('gf')
        
        item_str = f"{name} ${price:.2f}"
        if dietary_tags:
            item_str += f" ({','.join(dietary_tags)})"
        
        by_category[category].append(item_str)
    
    # Build summary
    for category, items in by_category.items():
        if items:
            summary_parts.append(f"{category}: {'; '.join(items[:5])}")
    
    return '\n'.join(summary_parts)

def get_available_categories(menu_items: List[Dict]) -> Dict[str, List[str]]:
    """Extract available categories from menu"""
    meal_times = set()
    course_types = set()
    food_categories = set()
    
    for item in menu_items:
        if 'meal_time' in item:
            meal_times.add(item['meal_time'])
        if 'subcategory' in item:
            course_types.add(item['subcategory'])
        if 'category' in item:
            food_categories.add(item['category'])
    
    # Add common categories that might be searched
    food_categories.update(['Pasta', 'Pizza', 'Seafood', 'Fish', 'Meat', 'Vegetarian', 'Vegan', 'Salad', 'Soup'])
    
    return {
        'meal_times': sorted(list(meal_times)) or ['Breakfast', 'Lunch', 'Dinner'],
        'course_types': sorted(list(course_types)) or ['starter', 'main', 'dessert'],
        'food_categories': sorted(list(food_categories))
    }

def get_available_dish_names(menu_items: List[Dict]) -> List[str]:
    """Extract all dish names for reference"""
    names = []
    for item in menu_items[:50]:  # Limit to prevent prompt overflow
        name = item.get('dish') or item.get('name')
        if name:
            names.append(name)
    return names

def get_customer_profile(db: Session, client_id: str, restaurant_id: str) -> Optional[Any]:
    """Get or create customer profile"""
    try:
        from models import CustomerProfile
        
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.client_id == client_id,
            CustomerProfile.restaurant_id == restaurant_id
        ).first()
        
        if not profile:
            profile = CustomerProfile(
                client_id=client_id,
                restaurant_id=restaurant_id,
                allergies=[],
                dietary_restrictions=[],
                preferences={}
            )
            db.add(profile)
            db.commit()
            db.refresh(profile)
        
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
    
    # Check for allergens in customer profile
    allergies = []
    dietary_restrictions = []
    
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary_restrictions = getattr(customer_profile, 'dietary_restrictions', []) or []
    
    all_restrictions = list(set(allergies + dietary_restrictions))
    context_data['all_restrictions'] = all_restrictions
    
    # Priority 1: Allergy/dietary context
    if all_restrictions:
        # Check if asking about safety
        safety_keywords = ['safe', 'can i eat', 'can i have', 'allergic', 'allergy', 'intolerant']
        if any(keyword in message_lower for keyword in safety_keywords):
            return "allergen_query", context_data
        
        # Check if correcting or removing allergies
        remove_keywords = ["don't have", "not allergic", "no allergy", "remove", "not actually"]
        if any(keyword in message_lower for keyword in remove_keywords):
            return "allergy_correction", context_data
        
        # Default to safety mode when restrictions exist
        return "allergen_safety", context_data
    
    # Priority 2: Check for allergen mentions in current message
    allergen_keywords = ['allergic', 'allergy', 'intolerant', 'can\'t eat', 'avoid']
    if any(keyword in message_lower for keyword in allergen_keywords):
        return "allergen_query", context_data
    
    # Priority 3: Food search
    if any(word in message_lower for word in ['menu', 'dish', 'food', 'eat', 'pasta', 'pizza', 'salad']):
        return "food_search", context_data
    
    # Default context
    return "general", context_data

def build_phase1_prompt(message: str, customer_profile: Any, chat_history: List[Dict], 
                       menu_items: List[Dict], restaurant_name: str) -> str:
    """Build Phase 1 prompt with restaurant context for tool AND parameter selection"""
    
    # Get available data
    categories = get_available_categories(menu_items)
    dish_names = get_available_dish_names(menu_items)
    
    prompt = f"""You are a tool selector for {restaurant_name}. 

CRITICAL INSTRUCTION: Focus PRIMARILY on the CURRENT MESSAGE intent. 
Only use conversation history when the current message explicitly references it (e.g., "I'll take it", "that one", "the first option").

CURRENT MESSAGE TO ANALYZE: "{message}"
"""
    
    # Add minimal customer info if relevant
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary = getattr(customer_profile, 'dietary_restrictions', []) or []
        
        if allergies or dietary:
            prompt += f"""
CUSTOMER INFO:
- Allergies: {', '.join(allergies) if allergies else 'none'}
- Dietary restrictions: {', '.join(dietary) if dietary else 'none'}
"""
    
    # Add conversation history for reference only
    if chat_history and len(chat_history) > 0:
        prompt += """
CONVERSATION HISTORY (for reference only if current message needs it):
"""
        for msg in chat_history[-3:]:  # Only last 3 messages
            role = "Customer" if msg["role"] == "user" else "Assistant"
            prompt += f"{role}: {msg['message']}\n"
    
    prompt += f"""
AVAILABLE TOOLS:

1. no_food_response - For greetings, goodbyes, thanks, general chat that doesn't involve food
   Parameters: 
   - response_type: "greeting" | "goodbye" | "thanks" | "hours" | "general"
   - include_hours: true/false (only for time-related queries)
   
   USE THIS TOOL FOR: hello, hi, good evening, bye, see you, thanks, perfect, great, ok, what time, when open/close

2. get_dish_details - Get info about a SPECIFIC dish
   Parameters: dish_name (can be partial like "carbonara" or have typos)
   
3. search_by_meal_time - Search dishes by when they're served
   Parameters: meal_time (from: {', '.join(categories['meal_times'])})
   
4. search_by_course_type - Search dishes by course
   Parameters: course_type (from: {', '.join(categories['course_types'])})
   
5. search_by_food_type - Search dishes by food category
   Parameters: food_type (from: {', '.join(categories['food_categories'])})
   
6. search_menu_by_ingredient - Search dishes containing ingredient
   Parameters: ingredient (any ingredient name)
   
7. filter_vegetarian/vegan/gluten_free/nut_free/dairy_free/shellfish_free - Filter safe dishes
   Parameters: none needed
   
8. update_allergy_add/remove - Update customer allergies
   Parameters: allergies (list), reason (for remove)
   
9. restaurant_info - Questions about restaurant/service
   Parameters: info_type (hours, location, contact, general)

PRIORITY RULES:
1. For greetings/goodbyes/thanks → ALWAYS use no_food_response
2. For food questions → use appropriate search/filter tools
3. For "I'll take it" type messages → check history and use get_dish_details

EXAMPLES:
- "Good evening" → [{{"tool": "no_food_response", "parameters": {{"response_type": "greeting"}}}}]
- "Perfect, see you soon!" → [{{"tool": "no_food_response", "parameters": {{"response_type": "goodbye"}}}}]
- "Thanks!" → [{{"tool": "no_food_response", "parameters": {{"response_type": "thanks"}}}}]
- "What time do you close?" → [{{"tool": "no_food_response", "parameters": {{"response_type": "hours", "include_hours": true}}}}]
- "What pasta do you have?" → [{{"tool": "search_by_food_type", "parameters": {{"food_type": "Pasta"}}}}]
- "I'm allergic to nuts" → [{{"tool": "update_allergy_add", "parameters": {{"allergies": ["nuts"]}}}}]

Respond with ONLY the JSON array."""
    
    return prompt

def execute_tool(tool_data: Dict, menu_items: List[Dict], customer_profile: Optional[Any] = None) -> Dict:
    """Execute a tool with given parameters"""
    tool_name = tool_data.get("tool")
    params = tool_data.get("parameters", {})
    
    logger.info(f"execute_tool called: tool={tool_name}, params={params}")
    
    # Handle no_food_response tool
    if tool_name == "no_food_response":
        response_type = params.get("response_type", "general")
        result = {
            "tool": tool_name,
            "response_type": response_type,
            "do_not_suggest_food": True,
            "suppress_allergies": True
        }
        
        if params.get("include_hours"):
            # In real implementation, fetch from database
            result["hours"] = "Monday-Sunday: 11:00 AM - 10:00 PM"
        
        return result
    
    # Get customer allergies if profile exists
    customer_allergies = []
    if customer_profile:
        customer_allergies = getattr(customer_profile, 'allergies', []) or []
        dietary_restrictions = getattr(customer_profile, 'dietary_restrictions', []) or []
        customer_allergies.extend(dietary_restrictions)
        customer_allergies = [str(a).lower() for a in customer_allergies if a]
    
    def is_safe_for_customer(item: Dict) -> bool:
        """Check if item is safe based on customer allergies"""
        if not customer_allergies:
            return True
        
        item_allergens = [a.lower() for a in item.get('allergens', [])]
        ingredients_text = ' '.join(item.get('ingredients', [])).lower()
        
        for allergy in customer_allergies:
            allergy_lower = allergy.lower()
            if any(allergy_lower in allergen for allergen in item_allergens):
                return False
            if allergy_lower in ingredients_text:
                return False
        
        return True
    
    if tool_name == "get_dish_details":
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
        
        # Try partial match
        matches = []
        for item in menu_items:
            item_name = (item.get('dish', '') or item.get('name', '')).lower()
            
            if dish_name in item_name or all(word in item_name for word in dish_name.split()):
                matches.append(item)
        
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
        elif len(matches) > 1:
            return {
                "tool": tool_name,
                "found": False,
                "error": "Multiple matches found",
                "suggestions": [m.get('dish') or m.get('name') for m in matches[:3]]
            }
        
        return {"tool": tool_name, "found": False, "error": "Dish not found"}
    
    elif tool_name == "search_by_food_type":
        food_type = params.get("food_type", "").lower()
        results = []
        
        for item in menu_items:
            item_category = item.get('category', '').lower()
            item_name = (item.get('dish', '') or item.get('name', '')).lower()
            
            # Check category and name
            if food_type in item_category or food_type in item_name:
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "description": item.get('description', ''),
                        "is_safe": True
                    })
        
        return {
            "tool": tool_name,
            "food_type": params.get("food_type"),
            "found": len(results),
            "items": results[:7]  # Limit results
        }
    
    elif tool_name == "search_by_meal_time":
        meal_time = params.get("meal_time", "").lower()
        results = []
        
        for item in menu_items:
            if item.get('meal_time', '').lower() == meal_time:
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "category": item.get('category', '')
                    })
        
        return {
            "tool": tool_name,
            "meal_time": params.get("meal_time"),
            "found": len(results),
            "items": results[:7]
        }
    
    elif tool_name == "search_by_course_type":
        course_type = params.get("course_type", "").lower()
        results = []
        
        for item in menu_items:
            if course_type in item.get('subcategory', '').lower():
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "category": item.get('category', '')
                    })
        
        return {
            "tool": tool_name,
            "course_type": params.get("course_type"),
            "found": len(results),
            "items": results[:7]
        }
    
    elif tool_name == "search_menu_by_ingredient":
        ingredient = params.get("ingredient", "").lower()
        results = []
        
        for item in menu_items:
            ingredients_text = ' '.join(item.get('ingredients', [])).lower()
            if ingredient in ingredients_text:
                if is_safe_for_customer(item):
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "ingredients": item.get('ingredients', [])
                    })
        
        return {
            "tool": tool_name,
            "ingredient": params.get("ingredient"),
            "found": len(results),
            "items": results[:7]
        }
    
    elif tool_name.startswith("filter_"):
        filter_type = tool_name.replace("filter_", "").replace("_", "-")
        results = []
        
        for item in menu_items:
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
            
            if suitable and is_safe_for_customer(item):
                results.append({
                    "name": item.get('dish') or item.get('name'),
                    "price": item.get('price'),
                    "category": item.get('category', '')
                })
        
        return {
            "tool": tool_name,
            "filter": filter_type,
            "found": len(results),
            "items": results[:7]
        }
    
    elif tool_name == "update_allergy_add":
        allergies = params.get("allergies", [])
        if customer_profile and allergies:
            existing = set(getattr(customer_profile, 'allergies', []) or [])
            existing.update(allergies)
            customer_profile.allergies = list(existing)
        
        return {
            "tool": tool_name,
            "success": True,
            "action": "added",
            "allergies": allergies
        }
    
    elif tool_name == "update_allergy_remove":
        allergies = params.get("allergies", [])
        reason = params.get("reason", "")
        
        if customer_profile and allergies:
            existing = set(getattr(customer_profile, 'allergies', []) or [])
            for allergy in allergies:
                existing.discard(allergy)
            customer_profile.allergies = list(existing)
        
        return {
            "tool": tool_name,
            "success": True,
            "action": "removed",
            "allergies": allergies,
            "reason": reason
        }
    
    elif tool_name == "restaurant_info":
        info_type = params.get("info_type", "general")
        
        info_responses = {
            "hours": "We're open Monday-Sunday from 11:00 AM to 10:00 PM",
            "location": "123 Main Street, Downtown",
            "contact": "Call us at (555) 123-4567",
            "general": f"Welcome to {restaurant_name}! We serve delicious food with a focus on quality and customer satisfaction."
        }
        
        return {
            "tool": tool_name,
            "info_type": info_type,
            "info": info_responses.get(info_type, info_responses["general"]),
            "found": True
        }
    
    return {"tool": tool_name, "error": "Unknown tool"}

def build_phase2_prompt(message: str, tool_results: List[Dict], restaurant_name: str, 
                       customer_profile: Any, context_type: str, context_data: Dict,
                       chat_history: List[Dict] = None) -> str:
    """Build Phase 2 prompt for final response generation"""
    
    # Check for no_food_response tool
    no_food_response = next((r for r in tool_results if r.get("tool") == "no_food_response"), None)
    
    if no_food_response:
        # Minimal context for non-food responses
        response_type = no_food_response.get("response_type", "general")
        
        prompt = f"""You are Maria at {restaurant_name}.

Customer said: "{message}"

STRICT RULES:
1. DO NOT suggest any food items or mention the menu
2. DO NOT mention allergies or dietary restrictions
3. Keep response brief, warm, and appropriate for a {response_type}
"""
        
        if response_type == "greeting":
            prompt += "\nGreet them warmly and ask how you can help (without suggesting food)."
        elif response_type == "goodbye":
            prompt += "\nSay goodbye warmly. If they ordered, wish them enjoyment. If not, invite them back."
        elif response_type == "thanks":
            prompt += "\nAcknowledge their thanks appropriately."
        elif response_type == "hours" and no_food_response.get("hours"):
            prompt += f"\nOur hours: {no_food_response['hours']}"
        
        prompt += "\n\nYour response:"
        return prompt
    
    # Regular food-related response
    # Context-specific intro
    if context_type == "allergen_safety":
        prompt = f"""You are Maria, a safety-conscious server at {restaurant_name}.
CRITICAL: Customer has restrictions: {', '.join(context_data.get('all_restrictions', []))}
"""
    else:
        prompt = f"""You are Maria, a warm and knowledgeable server at {restaurant_name}.
"""
    
    # Add conversation context
    if chat_history and len(chat_history) > 1:
        interaction_count = sum(1 for msg in chat_history if msg["role"] == "assistant")
        
        prompt += "RECENT CONVERSATION:\n"
        for msg in chat_history[-2:]:
            if msg["role"] == "user":
                prompt += f"Customer: {msg['message']}\n"
            else:
                prompt += f"You: {msg['message'][:100]}...\n"
        prompt += f"\n[This is interaction #{interaction_count + 1}]\n"
    
    prompt += f"""
Current request: "{message}"

MENU DATA FROM SEARCH:
"""
    
    # Format tool results
    has_results = False
    for result in tool_results:
        if result.get("tool") == "update_allergy_add":
            prompt += f"\nAllergies noted: {', '.join(result.get('allergies', []))}\n"
        elif result.get("tool") == "restaurant_info":
            prompt += f"\n{result.get('info_type', 'Info')}: {result.get('info', '')}\n"
        elif "items" in result and result.get("items"):
            has_results = True
            items = result["items"][:5]  # Limit items shown
            prompt += f"\nFrom {result.get('tool')} ({len(items)} items):\n"
            for item in items:
                prompt += f"- {item['name']} - ${item['price']:.2f}\n"
    
    if not has_results and not any(r.get("tool") in ["update_allergy_add", "restaurant_info"] for r in tool_results):
        prompt += "\nNo specific items found matching the request.\n"
    
    # Response guidelines
    prompt += """
RESPONSE GUIDELINES:
1. Be conversational and helpful
2. Mention 2-3 specific items with prices when relevant
3. For allergen contexts, emphasize safety
4. Keep responses concise (2-3 sentences)
5. Don't repeat allergy warnings unless directly relevant

Your response:"""
    
    return prompt

def mia_chat_service_internal_tools_v6(req: ChatRequest, db: Session) -> ChatResponse:
    """V6: Improved phase-based MIA chat with better non-food response handling"""
    
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
        
        logger.info(f"=== V6 2-Phase System - Restaurant: {req.restaurant_id} ===")
        logger.info(f"Context: {context_type}, Menu items: {len(menu_items)}")
        
        # === PHASE 1: Tool Selection ===
        logger.info("PHASE 1: Tool selection")
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
        
        # Parse tool selection
        response_data = response.json()
        selection_text = response_data.get("response", "")
        
        if selection_text is None:
            selection_text = ""
        
        selection_text = selection_text.strip()
        
        try:
            selected_tools = json.loads(selection_text)
            if not isinstance(selected_tools, list):
                selected_tools = [{"tool": "no_food_response", "parameters": {"response_type": "general"}}]
        except:
            selected_tools = [{"tool": "no_food_response", "parameters": {"response_type": "general"}}]
        
        logger.info(f"Selected tools: {selected_tools}")
        
        # Update allergies in database if needed
        for tool_data in selected_tools:
            if tool_data.get("tool") in ["update_allergy_add", "update_allergy_remove"]:
                try:
                    allergies = tool_data.get("parameters", {}).get("allergies", [])
                    if allergies and customer_profile:
                        if tool_data.get("tool") == "update_allergy_add":
                            existing_allergies = set(customer_profile.allergies or [])
                            existing_allergies.update(allergies)
                            customer_profile.allergies = list(existing_allergies)
                            db.commit()
                        else:
                            existing_allergies = set(customer_profile.allergies or [])
                            for allergy in allergies:
                                existing_allergies.discard(allergy)
                            customer_profile.allergies = list(existing_allergies)
                            db.commit()
                except Exception as e:
                    logger.error(f"Failed to update allergies: {e}")
        
        # === Execute Tools ===
        tool_results = []
        for tool_data in selected_tools:
            result = execute_tool(tool_data, menu_items, customer_profile)
            tool_results.append(result)
            logger.info(f"Tool {tool_data.get('tool')} executed")
        
        # === PHASE 2: Response Generation ===
        logger.info("PHASE 2: Response generation")
        
        phase2_prompt = build_phase2_prompt(
            req.message, tool_results, restaurant_name, 
            customer_profile, context_type, context_data, chat_history
        )
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": phase2_prompt,
                "max_tokens": 200,
                "temperature": 0.7
            },
            timeout=30
        )
        
        if response.status_code == 200:
            answer = response.json().get("response", "")
            
            # Validate response
            is_safe, validation_message = validate_response(
                answer,
                getattr(customer_profile, 'allergies', []) if customer_profile else [],
                tool_results
            )
            
            if not is_safe:
                logger.error(f"Safety validation failed: {validation_message}")
                answer = "I apologize, but I need to be more careful with your dietary restrictions. Let me know what you'd like to know about our menu."
            
            # Add debug info
            debug_info = {
                "version": "v6",
                "flow": "no_food_response" if any(r.get("tool") == "no_food_response" for r in tool_results) else "tool_flow",
                "phase1_tools_selected": selected_tools,
                "context_type": context_type,
                "customer_allergies": getattr(customer_profile, 'allergies', []) if customer_profile else [],
                "response_time": f"{time.time() - start_time:.2f}s"
            }
            
            # Add tool results summary
            if tool_results and not any(r.get("tool") == "no_food_response" for r in tool_results):
                debug_info["tool_results_summary"] = []
                for result in tool_results:
                    if "items" in result:
                        debug_info["tool_results_summary"].append({
                            "tool": result.get("tool"),
                            "items_found": len(result.get("items", [])),
                            "found": result.get("found", 0)
                        })
                    else:
                        debug_info["tool_results_summary"].append({
                            "tool": result.get("tool"),
                            "items_found": "N/A",
                            "found": result.get("found")
                        })
            
            answer += f"\n\n[DEBUG INFO]\n{json.dumps(debug_info, indent=2)}"
            
            return ChatResponse(
                answer=answer,
                response_id=response_data.get("id"),
                confidence_score=0.95
            )
        else:
            logger.error(f"Phase 2 failed with status {response.status_code}")
            return ChatResponse(
                answer="I apologize, but I'm having trouble responding right now. Please try again.",
                response_id=None,
                confidence_score=0.0
            )
            
    except Exception as e:
        logger.error(f"V6 2-Phase error: {str(e)}", exc_info=True)
        return ChatResponse(
            answer="I apologize, but I encountered an error. Please try again.",
            response_id=None,
            confidence_score=0.0
        )