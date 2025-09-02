"""
MIA Chat Service - Context Enhanced with State Line
Implements improved context retention with pronouns, categories, and diets
"""
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse

# Import existing functions
from services.mia_chat_service_full_menu import build_compact_menu_context
from services.mia_chat_service_hybrid import (
    get_mia_response_hybrid,
    MIA_BACKEND_URL
)
from services.customer_memory_service import CustomerMemoryService
import requests

logger = logging.getLogger(__name__)

# Tool definitions (stable schemas - DO NOT CHANGE KEYS)
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dish_details",
            "description": "Get detailed information about a specific dish",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish": {
                        "type": "string",
                        "description": "Name of the dish"
                    }
                },
                "required": ["dish"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_menu_items",
            "description": "Search menu items by ingredient, category, or name",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "What to search for"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["name", "ingredient", "category"],
                        "description": "Type of search"
                    }
                },
                "required": ["search_term", "search_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_dietary",
            "description": "Filter menu items by dietary restriction",
            "parameters": {
                "type": "object",
                "properties": {
                    "diet": {
                        "type": "string",
                        "description": "Dietary restriction (vegan, vegetarian, gluten-free, etc.)"
                    }
                },
                "required": ["diet"]
            }
        }
    }
]

# Bella Vista dish aliases (10-30 mappings)
DISH_ALIASES = {
    # Pasta aliases
    "carbonara": "Spaghetti Carbonara",
    "alfredo": "Fettuccine Alfredo",
    "arrabbiata": "Penne Arrabbiata",
    "vongole": "Linguine alle Vongole",
    "bolognese": "Lasagna Bolognese",
    
    # Seafood aliases
    "tuna": "Tuna Steak",
    "salmon": "Grilled Salmon",
    "scallops": "Seared Scallops",
    "octopus": "Grilled Octopus",
    "lobster bisque": "Lobster Bisque",
    
    # Meat aliases
    "ribeye": "Grilled Ribeye",
    "filet": "Filet Mignon",
    "osso buco": "Osso Buco",
    "lamb": "Lamb Chops",
    "duck": "Duck Confit",
    
    # Appetizer aliases
    "arancini": "Truffle Arancini",
    "caprese": "Caprese Skewers",
    "calamari": "Calamari Fritti",
    "bruschetta": "Bruschetta Trio",
    
    # Dessert aliases
    "tiramisu": "Tiramisu",
    "cheesecake": "New York Cheesecake",
    "lava cake": "Chocolate Lava Cake",
    "creme brulee": "Crème Brûlée",
    
    # Common misspellings
    "fetuccini": "Fettuccine Alfredo",
    "carbonera": "Spaghetti Carbonara",
    "panna cota": "Panna Cotta",
    "cesar salad": "Caesar Salad",
    "risoto": "Mushroom Risotto"
}

def normalize_dish_name(dish_name: str) -> str:
    """Normalize dish name using aliases"""
    dish_lower = dish_name.lower().strip()
    
    # Check exact alias match
    if dish_lower in DISH_ALIASES:
        return DISH_ALIASES[dish_lower]
    
    # Check if any alias is contained in the input
    for alias, canonical in DISH_ALIASES.items():
        if alias in dish_lower:
            return canonical
    
    # Return original if no alias found
    return dish_name

def extract_context_state(messages: List[models.ChatMessage], current_message: str, menu_items: List[Dict]) -> Dict:
    """Extract context state from conversation history"""
    context = {
        "LastDish": None,
        "Category": None,
        "Options": None,
        "ActiveDiet": None
    }
    
    # Look for diet mentions in recent messages
    diet_keywords = {
        "vegan": "vegan",
        "vegetarian": "vegetarian",
        "gluten-free": "gluten-free",
        "gluten free": "gluten-free",
        "dairy-free": "dairy-free",
        "dairy free": "dairy-free",
        "nut-free": "nut-free",
        "nut free": "nut-free",
        "keto": "keto",
        "paleo": "paleo"
    }
    
    # Check current message for diet
    current_lower = current_message.lower()
    for keyword, diet_tag in diet_keywords.items():
        if keyword in current_lower:
            context["ActiveDiet"] = diet_tag
            break
    
    # Look through recent messages for context
    for msg in messages[:10]:  # Last 10 messages
        msg_lower = msg.message.lower()
        
        # Check for diet persistence
        if not context["ActiveDiet"]:
            for keyword, diet_tag in diet_keywords.items():
                if keyword in msg_lower and msg.sender_type == "client":
                    context["ActiveDiet"] = diet_tag
                    break
        
        # Extract last mentioned dish from AI responses
        if msg.sender_type == "ai":
            for item in menu_items:
                dish_name = item.get('dish') or item.get('name', '')
                if dish_name and dish_name in msg.message:
                    context["LastDish"] = dish_name
                    break
        
        # Check for category mentions
        categories = ["pasta", "seafood", "meat", "appetizers", "desserts", "salads", "soups"]
        for cat in categories:
            if cat in msg_lower:
                context["Category"] = cat.capitalize()
                break
    
    # Check if current message is ambiguous
    ambiguous_phrases = ["more", "details", "that", "it", "tell me about", "information", "yes"]
    is_ambiguous = any(phrase in current_lower for phrase in ambiguous_phrases)
    
    # If ambiguous and we have multiple recent dishes, set Options
    if is_ambiguous and not context["LastDish"]:
        recent_dishes = []
        for msg in messages[:5]:
            if msg.sender_type == "ai":
                for item in menu_items:
                    dish_name = item.get('dish') or item.get('name', '')
                    if dish_name and dish_name in msg.message and dish_name not in recent_dishes:
                        recent_dishes.append(dish_name)
        
        if len(recent_dishes) >= 2:
            context["Options"] = " | ".join(recent_dishes[:3])
    
    return context

def format_context_line(context: Dict) -> str:
    """Format context state into a single line"""
    parts = []
    
    if context.get("LastDish"):
        parts.append(f'LastDish="{context["LastDish"]}"')
    
    if context.get("Category"):
        parts.append(f'Category="{context["Category"]}"')
    
    if context.get("Options"):
        parts.append(f'Options="{context["Options"]}"')
    
    if context.get("ActiveDiet"):
        parts.append(f'ActiveDiet="{context["ActiveDiet"]}"')
    
    if parts:
        return "Context: " + " | ".join(parts)
    
    return ""

def execute_tool(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool and return results"""
    try:
        if tool_name == "get_dish_details":
            # Normalize dish name
            requested_dish = normalize_dish_name(parameters.get("dish", ""))
            
            # Find exact match
            for item in menu_items:
                item_name = item.get('dish') or item.get('name', '')
                if item_name.lower() == requested_dish.lower():
                    return {
                        "success": True,
                        "dish": {
                            "name": item_name,
                            "price": item.get('price', ''),
                            "description": item.get('description', ''),
                            "ingredients": item.get('ingredients', []),
                            "allergens": item.get('allergens', []),
                            "category": item.get('subcategory') or item.get('category', '')
                        }
                    }
            
            return {
                "success": False,
                "error": f"Dish '{requested_dish}' not found"
            }
        
        elif tool_name == "search_menu_items":
            search_term = parameters.get("search_term", "").lower()
            search_type = parameters.get("search_type", "ingredient")
            
            results = []
            for item in menu_items:
                match = False
                
                if search_type == "name":
                    dish_name = (item.get('dish') or item.get('name', '')).lower()
                    match = search_term in dish_name
                elif search_type == "category":
                    category = (item.get('category') or '').lower()
                    subcategory = (item.get('subcategory') or '').lower()
                    restaurant_cat = (item.get('restaurant_category') or '').lower()
                    match = search_term in category or search_term in subcategory or search_term in restaurant_cat
                else:  # ingredient
                    ingredients = item.get('ingredients', [])
                    if isinstance(ingredients, list):
                        match = any(search_term in ing.lower() for ing in ingredients)
                
                if match:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "brief": f"{item.get('dish', '')} - {item.get('price', '')}"
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results[:10]  # Limit to 10 items
            }
        
        elif tool_name == "filter_by_dietary":
            diet = parameters.get("diet", "").lower()
            results = []
            
            # Normalize diet names
            diet_map = {
                "vegan": "is_vegan",
                "vegetarian": "is_vegetarian",
                "gluten-free": "is_gluten_free",
                "gluten free": "is_gluten_free",
                "dairy-free": "is_dairy_free",
                "dairy free": "is_dairy_free",
                "nut-free": "is_nut_free",
                "nut free": "is_nut_free"
            }
            
            diet_field = diet_map.get(diet)
            
            for item in menu_items:
                suitable = False
                
                if diet_field and item.get(diet_field) is True:
                    suitable = True
                elif diet in ["keto", "paleo"]:
                    dietary_tags = item.get('dietary_tags', [])
                    if diet in dietary_tags:
                        suitable = True
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "brief": f"{item.get('dish', '')} - {item.get('price', '')}"
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }

def send_to_mia_with_context(prompt: str, tools: List[Dict], context: Dict, is_tool_decision: bool = True) -> Tuple[str, bool, Optional[Dict]]:
    """Send request to MIA with proper settings based on turn type"""
    try:
        # Dynamic settings based on turn type
        if is_tool_decision:
            # Tool-decision turn: very focused
            request_data = {
                "message": prompt,
                "context": context,
                "tools": tools,
                "tool_choice": "auto",
                "max_tokens": 64,
                "temperature": 0.1,
                "top_p": 0.3
            }
        else:
            # Final prose turn: more creative
            request_data = {
                "message": prompt,
                "context": context,
                "tools": [],  # No tools for final response
                "max_tokens": 200,
                "temperature": 0.4,
                "top_p": 1.0
            }
        
        logger.info(f"Sending to MIA (tool_decision={is_tool_decision})")
        
        # Send to MIA backend
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-context-enhanced"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            
            if job_id:
                # Poll for result
                for i in range(30):
                    time.sleep(1)
                    
                    poll_response = requests.get(
                        f"{MIA_BACKEND_URL}/job/{job_id}/result",
                        timeout=5
                    )
                    
                    if poll_response.status_code == 200:
                        poll_result = poll_response.json()
                        
                        if poll_result.get("status") == "completed":
                            result_data = poll_result.get("result", {})
                            
                            # Check for tool call
                            if result_data.get("tool_call"):
                                return result_data.get("response", ""), True, result_data["tool_call"]
                            
                            return result_data.get("response", ""), False, None
            
            # Direct response
            return result.get("response", str(result)), False, None
        
        else:
            logger.error(f"MIA error: {response.status_code}")
            return f"Service error: {response.status_code}", False, None
    
    except Exception as e:
        logger.error(f"Error calling MIA: {e}")
        return "Service temporarily unavailable", False, None

def generate_response_context_enhanced(req: ChatRequest, db: Session) -> ChatResponse:
    """Generate response using context-enhanced orchestration"""
    try:
        logger.info(f"CONTEXT ENHANCED - Request from {req.client_id}: {req.message[:50]}...")
        
        # Update todo
        from services.todo_service import update_todo_status
        update_todo_status(db, 11, "in_progress")
        
        # Get restaurant and menu data
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant or not restaurant.data:
            return ChatResponse(answer="I'm sorry, but I couldn't find the restaurant information.")
        
        # Extract restaurant data
        restaurant_data = restaurant.data if isinstance(restaurant.data, dict) else json.loads(restaurant.data)
        business_name = restaurant_data.get('business_name', 'our restaurant')
        menu_items = restaurant_data.get('menu', [])
        
        # Get customer profile
        client_id_str = str(req.client_id)
        customer_profile = db.query(models.CustomerProfile).filter(
            models.CustomerProfile.client_id == client_id_str,
            models.CustomerProfile.restaurant_id == req.restaurant_id
        ).first()
        
        # Get customer context
        customer_context = CustomerMemoryService.get_customer_context(customer_profile)
        
        # Build compact menu context
        menu_context = build_compact_menu_context(menu_items, restaurant_data.get('business_type', 'restaurant'))
        
        # Build dish aliases block
        dish_aliases_block = "\n".join([f'"{alias}" -> "{canonical}"' for alias, canonical in DISH_ALIASES.items()])
        
        # Get recent chat history
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
        
        # Extract context state
        context_state = extract_context_state(recent_messages, req.message, menu_items)
        context_line = format_context_line(context_state)
        
        # Build system context with new prompt
        system_context = {
            "business_name": business_name,
            "restaurant_name": business_name,
            "system_prompt": f"""You are Maria, a friendly server at {business_name}.

Tool use (AI decides)

If the guest asks for details ("more info", "details", "tell me about", "information", or says "yes" after you offered details), use get_dish_details(dish).

Always consider conversation history. If a specific dish is being discussed and the guest wants details, call get_dish_details for that dish.

If the guest asks by ingredient, category, or name ("fish", "chicken", "vegetarian", "pasta", "pizza", "seafood"), use search_menu_items(search_term, search_type in {{ingredient, category, name}}).

If the guest asks by dietary need, use filter_by_dietary(diet).

For greetings and small talk, respond naturally without tools.

If a tool returns "not found" or the item isn't on our menu, be honest and suggest close alternatives.

Partial and misspellings
• Normalize names (case/accents/spaces); tolerate common typos (for example, "fetuticini carbonera" should map to "Spaghetti Carbonara").
• If a single dish is clearly intended, call get_dish_details with the canonical dish and add a soft confirmation.
• If unsure, first call search_menu_items with search_type = name; if it returns one plausible dish, then call get_dish_details. If multiple, ask one brief clarifying question (no tool yet).

Context state line (one hint may be appended to the user message)
You may receive a single line in this format:
Context: LastDish="{{dish or null}}" | Category="{{category or null}}" | Options="{{dish1 | dish2 | dish3 or null}}" | ActiveDiet="{{diet tag or none}}"

Action rules for the context line
• If LastDish is present and the user says "more", "details", "that", "it", or "yes", call get_dish_details(dish = LastDish) and begin your reply with: About {{LastDish}}…
• If Options is present with two or more items and the user asks "more/details/that/it", do not choose; ask which one (list up to three options).
• If Category is present and there is no LastDish, call search_menu_items(search_type = category, search_term = Category) and then ask the guest to pick.
• If ActiveDiet is present, always call filter_by_dietary(diet = ActiveDiet) before recommending anything. Never recommend items that violate the diet.

Style and output
• Be concise, warm, and accurate. Never invent items—use tools.
• After a tool returns, summarize the most relevant points (no more than five items, or two to three sentences) and end with a helpful question.
• Do not print tool JSON or tags—use the tools interface only.
• If unsure, ask one short clarification.

Menu (compact or compressed)
{menu_context}

Customer profile
{customer_context}

Dish aliases (for canonicalization; keep short, 10–30 mappings)
{dish_aliases_block}"""
        }
        
        # Build conversation context
        chat_history = []
        for msg in reversed(recent_messages[1:]):  # Skip current message
            if msg.sender_type == "client":
                chat_history.append(f"Customer: {msg.message}")
            elif msg.sender_type == "ai":
                chat_history.append(f"Maria: {msg.message}")
        
        conversation_context = "\n".join(chat_history) if chat_history else ""
        
        # Build prompt with context line
        user_message = req.message
        if context_line:
            user_message = f"{req.message}\n{context_line}"
        
        full_prompt = f"Customer: {user_message}"
        if conversation_context:
            full_prompt = f"Recent conversation:\n{conversation_context}\n\n{full_prompt}"
        
        # Send for tool decision (with tools)
        response, used_tools, tool_call = send_to_mia_with_context(
            full_prompt,
            AVAILABLE_TOOLS,
            system_context,
            is_tool_decision=True
        )
        
        # If tool was called, execute it
        if used_tools and tool_call:
            tool_name = tool_call.get("name")
            parameters = tool_call.get("parameters", {})
            
            logger.info(f"Executing tool: {tool_name} with params: {parameters}")
            tool_result = execute_tool(tool_name, parameters, menu_items)
            
            # Format tool result for final response
            if tool_result.get("success"):
                if tool_name == "get_dish_details":
                    dish = tool_result.get("dish", {})
                    tool_summary = f"Found details for {dish.get('name')}: {dish.get('description')} Price: {dish.get('price')}"
                    if dish.get('ingredients'):
                        tool_summary += f" Ingredients: {', '.join(dish['ingredients'][:5])}"
                
                elif tool_name == "search_menu_items":
                    items = tool_result.get("items", [])
                    if items:
                        tool_summary = f"Found {len(items)} items: " + ", ".join([item['name'] for item in items[:5]])
                    else:
                        tool_summary = "No items found matching your search"
                
                elif tool_name == "filter_by_dietary":
                    items = tool_result.get("items", [])
                    if items:
                        tool_summary = f"Found {len(items)} options: " + ", ".join([item['name'] for item in items[:5]])
                    else:
                        tool_summary = "No items found for that dietary restriction"
            else:
                tool_summary = tool_result.get("error", "Tool error")
            
            # Send for final prose (without tools)
            follow_up_prompt = f"""Tool result: {tool_summary}

Customer's original question: {req.message}

Please provide a natural, friendly response based on this information. Be concise and end with a helpful question."""
            
            final_response, _, _ = send_to_mia_with_context(
                follow_up_prompt,
                [],  # No tools
                system_context,
                is_tool_decision=False
            )
            
            response = final_response
        
        # Extract and update customer profile if needed
        extracted_info = CustomerMemoryService.extract_customer_info(req.message)
        if extracted_info:
            CustomerMemoryService.update_customer_profile(
                db, req.client_id, req.restaurant_id, extracted_info
            )
        
        # Mark task complete
        update_todo_status(db, 11, "completed")
        
        return ChatResponse(answer=response)
    
    except Exception as e:
        logger.error(f"Error in context enhanced service: {e}", exc_info=True)
        return ChatResponse(answer="I apologize, but I'm having trouble processing your request. Please try again.")

# Export the enhanced function
mia_chat_service_context_enhanced = generate_response_context_enhanced