"""
MIA Chat Service - Simplified Tool Approach
Only tools for actual data retrieval, AI handles dietary filtering directly
"""
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Set
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse

# Import base functionality
from services.mia_chat_service_full_menu import (
    build_compact_menu_context,
    mia_chat_service_full_menu
)
from services.mia_chat_service_hybrid import (
    get_mia_response_hybrid,
    HybridCache,
    get_or_create_client,
    MIA_BACKEND_URL
)
from services.customer_memory_service import CustomerMemoryService
import models
import requests

logger = logging.getLogger(__name__)

# Only tools that actually need backend data retrieval
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dish_details",
            "description": "Use this when customer asks for 'more info', 'details', 'tell me about' a specific dish, OR when they say 'yes' to your offer for more information. Returns complete details including full description, all ingredients, preparation method, and allergens",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish": {
                        "type": "string",
                        "description": "Name of the dish to get details for"
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
            "description": "Search for menu items by ingredient, category, or name when you need to find specific items",
            "parameters": {
                "type": "object",
                "properties": {
                    "search_term": {
                        "type": "string",
                        "description": "What to search for (e.g., 'pasta', 'chicken', 'vegetarian')"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["name", "ingredient", "category"],
                        "description": "Type of search to perform"
                    }
                },
                "required": ["search_term", "search_type"]
            }
        }
    }
    # Removed filter_by_dietary - AI will handle this directly
]

# Dish aliases for canonicalization
DISH_ALIASES = {
    "carbonara": "Spaghetti Carbonara",
    "tuna": "Tuna Steak",
    "mushroom risotto": "Wild Mushroom Risotto",
    "lobster pasta": "Lobster Ravioli",
    "salmon": "Grilled Salmon",
    "scallops": "Seared Scallops",
    "caesar": "Caesar Salad",
    "bruschetta": "Bruschetta Trio",
    "french onion": "French Onion Soup",
    "minestrone": "Minestrone Soup",
    "chicken parm": "Chicken Parmesan",
    "eggplant parm": "Eggplant Parmesan",
    "ribeye": "Ribeye Steak",
    "filet": "Filet Mignon",
    "lamb": "Grilled Lamb Chops",
    "halibut": "Pan-Seared Halibut",
    "lava cake": "Chocolate Lava Cake",
    "cheesecake": "New York Cheesecake",
    "tiramisu": "Tiramisu",
    "creme brulee": "Crème Brûlée",
    "veal": "Veal Piccata",
    "short ribs": "Braised Short Ribs",
    "duck": "Duck Confit",
    "octopus": "Grilled Octopus",
    "beef wellington": "Beef Wellington",
    "pork": "Pork Tenderloin"
}

def get_dish_aliases_block() -> str:
    """Generate the dish aliases block for the system prompt"""
    lines = []
    for alias, canonical in DISH_ALIASES.items():
        lines.append(f'"{alias}" -> "{canonical}"')
    return "\n".join(lines)

def build_dish_details_response(item: Dict) -> Dict:
    """Build a successful dish details response"""
    details = {
        "name": item.get('dish') or item.get('name', ''),
        "price": item.get('price', ''),
        "description": item.get('description', ''),
        "ingredients": item.get('ingredients', []),
        "allergens": item.get('allergens', []),
        "category": item.get('subcategory') or item.get('category', ''),
        "preparation": item.get('preparation', ''),
        "serving_size": item.get('serving_size', ''),
        "calories": item.get('calories', ''),
        "spice_level": item.get('spice_level', ''),
        "recommended_wine": item.get('wine_pairing', '')
    }
    
    # Remove empty fields
    details = {k: v for k, v in details.items() if v}
    
    return {
        "success": True,
        "dish": details
    }

def canonicalize_dish_name(name: str) -> str:
    """Convert common aliases to canonical dish names"""
    name_lower = name.lower().strip()
    
    # Check direct aliases
    if name_lower in DISH_ALIASES:
        return DISH_ALIASES[name_lower]
    
    # Check if the name contains an alias
    for alias, canonical in DISH_ALIASES.items():
        if alias in name_lower:
            return canonical
    
    return name

def execute_tool(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool and return results"""
    try:
        if tool_name == "get_dish_details":
            requested_dish = parameters.get("dish", "")
            
            # Canonicalize the dish name
            canonical_dish = canonicalize_dish_name(requested_dish)
            requested_lower = canonical_dish.lower().strip()
            
            # Try exact match first (case-insensitive)
            for item in menu_items:
                item_name = item.get('dish') or item.get('name', '')
                if requested_lower == item_name.lower():
                    return build_dish_details_response(item)
            
            # Try fuzzy matching
            best_match = None
            best_score = 0
            
            # Remove common cooking prefixes
            cooking_words = ['seared', 'grilled', 'baked', 'fried', 'roasted', 'steamed', 'pan-seared']
            normalized_request = requested_lower
            for word in cooking_words:
                normalized_request = normalized_request.replace(word + ' ', '')
            
            for item in menu_items:
                item_name = item.get('dish') or item.get('name', '')
                item_lower = item_name.lower()
                
                # Normalize item name too
                normalized_item = item_lower
                for word in cooking_words:
                    normalized_item = normalized_item.replace(word + ' ', '')
                
                # Calculate match score
                score = 0
                
                if normalized_request in normalized_item or normalized_item in normalized_request:
                    score = 0.9
                elif requested_lower in item_lower or item_lower in requested_lower:
                    score = 0.8
                else:
                    # Word overlap check
                    request_words = set(normalized_request.split())
                    item_words = set(normalized_item.split())
                    if request_words and item_words:
                        overlap = len(request_words.intersection(item_words))
                        if overlap > 0:
                            score = overlap / max(len(request_words), len(item_words))
                
                if score > best_score:
                    best_score = score
                    best_match = (item, item_name)
            
            if best_match and best_score > 0.7:
                return build_dish_details_response(best_match[0])
            
            return {
                "success": False,
                "error": f"Dish '{requested_dish}' not found. Please check the menu for available items."
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
                    match = search_term in category or search_term in subcategory
                else:  # ingredient
                    ingredients = item.get('ingredients', [])
                    if isinstance(ingredients, list):
                        match = any(search_term in ing.lower() for ing in ingredients)
                    elif isinstance(ingredients, str):
                        match = search_term in ingredients.lower()
                
                if match:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "brief": f"{item.get('dish', '')} - {item.get('price', '')}"
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results[:15]
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

def extract_context_state(recent_messages: List[models.ChatMessage], menu_items: List[Dict], current_message: str) -> Dict[str, str]:
    """Extract context state from recent messages"""
    state = {}
    
    # Track last discussed dish
    last_dish = None
    last_category = None
    candidates = []
    diet = None
    
    # Check for dietary restrictions in current message
    diet_keywords = {
        "vegan": "vegan",
        "vegetarian": "vegetarian", 
        "gluten-free": "gluten-free",
        "gluten free": "gluten-free",
        "dairy-free": "dairy-free",
        "dairy free": "dairy-free",
        "nut-free": "nut-free",
        "nut free": "nut-free"
    }
    
    current_lower = current_message.lower()
    for keyword, diet_tag in diet_keywords.items():
        if keyword in current_lower:
            diet = diet_tag
            break
    
    # Look through recent messages (most recent first)
    for msg in recent_messages[:10]:
        if msg.sender_type == "ai":
            # Check if AI mentioned specific dishes
            ai_text = msg.message
            for item in menu_items:
                dish_name = item.get('dish') or item.get('name', '')
                if dish_name and dish_name in ai_text:
                    if not last_dish:
                        last_dish = dish_name
                    break
            
            # Check if AI mentioned categories
            categories = ["pasta", "pizza", "seafood", "salad", "appetizer", "dessert", "soup", "sandwich", "starter", "main", "dinner"]
            for cat in categories:
                if cat in ai_text.lower() and not last_category:
                    last_category = cat
                    break
        
        elif msg.sender_type == "client":
            # Check for dietary restrictions in history
            if not diet:
                client_lower = msg.message.lower()
                for keyword, diet_tag in diet_keywords.items():
                    if keyword in client_lower:
                        diet = diet_tag
                        break
    
    # Check if current message is asking about a category
    category_keywords = ["pasta", "pizza", "seafood", "salad", "appetizer", "dessert", "soup", "sandwich", "starter", "main", "dinner"]
    for cat in category_keywords:
        if cat in current_lower:
            last_category = cat
            # Find all items in this category
            cat_items = []
            for item in menu_items:
                if cat in (item.get('category', '').lower() + ' ' + item.get('subcategory', '').lower()):
                    cat_items.append(item.get('dish') or item.get('name', ''))
            if len(cat_items) > 1:
                candidates = cat_items[:3]  # Top 3 candidates
            break
    
    # Build state dict
    if last_dish:
        state["LastDish"] = last_dish
    if last_category:
        state["LastCategory"] = last_category
    if candidates:
        state["Candidates"] = "|".join(candidates)
    if diet:
        state["Diet"] = diet
    
    return state

def format_context_state_line(state: Dict[str, str]) -> str:
    """Format context state into a single line"""
    if not state:
        return ""
    
    parts = []
    if "LastDish" in state:
        parts.append(f'LastDish="{state["LastDish"]}"')
    if "LastCategory" in state:
        parts.append(f'LastCategory="{state["LastCategory"]}"')
    if "Candidates" in state:
        parts.append(f'Candidates="{state["Candidates"]}"')
    if "Diet" in state:
        parts.append(f'Diet="{state["Diet"]}"')
    
    if parts:
        return f"[Context: {'; '.join(parts)}]"
    return ""

def format_tool_result(tool_name: str, result: Dict) -> str:
    """Format tool result into natural language"""
    if not result.get("success"):
        return f"I couldn't find that information: {result.get('error', 'Unknown error')}"
    
    if tool_name == "get_dish_details":
        dish = result.get("dish", {})
        parts = [f"Here's what I found about {dish.get('name', 'the dish')}:"]
        
        if dish.get('price'):
            parts.append(f"Price: {dish['price']}")
        if dish.get('description'):
            parts.append(f"Description: {dish['description']}")
        if dish.get('ingredients'):
            parts.append(f"Ingredients: {', '.join(dish['ingredients'])}")
        if dish.get('allergens'):
            parts.append(f"Allergens: {', '.join(dish['allergens'])}")
        if dish.get('preparation'):
            parts.append(f"Preparation: {dish['preparation']}")
        if dish.get('spice_level'):
            parts.append(f"Spice Level: {dish['spice_level']}")
        
        return "\n".join(parts)
    
    elif tool_name == "search_menu_items":
        items = result.get("items", [])
        if not items:
            return "I couldn't find any items matching your search."
        
        response = f"I found {result.get('count', 0)} items:\n"
        response += "\n".join([f"- {item['brief']}" for item in items])
        return response
    
    return str(result)

def send_to_mia_with_tools(prompt: str, tools: List[Dict], context: Dict, decoding_params: Dict) -> Tuple[str, bool, Optional[Dict]]:
    """
    Send request to MIA with proper tool support and specific decoding parameters
    Returns: (response_text, used_tools, tool_call_info)
    """
    try:
        # Prepare the chat request with tools
        request_data = {
            "message": prompt,
            "context": context,
            "tools": tools,
            "tool_choice": "auto",
            **decoding_params  # Include temperature, top_p, max_tokens
        }
        
        logger.info(f"Sending to MIA with {len(tools)} tools and params: {decoding_params}")
        
        # Send to MIA backend
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-tools"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            
            if job_id:
                logger.info(f"Job queued: {job_id}, polling for result...")
                
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
                                logger.info(f"Tool call detected: {result_data['tool_call']}")
                                return result_data.get("response", ""), True, result_data["tool_call"]
                            
                            return result_data.get("response", ""), False, None
            
            # Direct response (no job)
            return result.get("response", str(result)), False, None
        
        else:
            logger.error(f"MIA error: {response.status_code} - {response.text}")
            return f"Service error: {response.status_code}", False, None
    
    except Exception as e:
        logger.error(f"Error calling MIA with tools: {e}")
        # Fall back to regular response
        return get_mia_response_hybrid(prompt, decoding_params), False, None

def check_menu_output_guard(response: str, menu_items: List[Dict]) -> Tuple[bool, str]:
    """
    Optional output guard to check if response mentions dishes not on menu
    Returns: (is_valid, corrected_response)
    """
    # Extract all dish names from menu
    valid_dishes = set()
    for item in menu_items:
        dish_name = item.get('dish') or item.get('name', '')
        if dish_name:
            valid_dishes.add(dish_name.lower())
    
    # Quick check - if response doesn't seem to mention specific dishes, it's fine
    response_lower = response.lower()
    
    # Look for potential dish mentions (capitalized food items)
    import re
    potential_dishes = re.findall(r'\b([A-Z][a-z]+ (?:[A-Z][a-z]+ )?(?:Steak|Salad|Soup|Pasta|Pizza|Cake|Tart|Ravioli|Risotto))\b', response)
    
    if not potential_dishes:
        return True, response
    
    # Check each potential dish
    invalid_dishes = []
    for dish in potential_dishes:
        if dish.lower() not in valid_dishes:
            # Check if it's close to a valid dish
            close_match = False
            for valid in valid_dishes:
                if dish.lower() in valid or valid in dish.lower():
                    close_match = True
                    break
            
            if not close_match:
                invalid_dishes.append(dish)
    
    if invalid_dishes:
        # Find closest matches
        suggestions = []
        for invalid in invalid_dishes[:1]:  # Just handle the first one
            # Find dishes with word overlap
            invalid_words = set(invalid.lower().split())
            best_matches = []
            
            for item in menu_items:
                dish_name = item.get('dish') or item.get('name', '')
                dish_words = set(dish_name.lower().split())
                
                if invalid_words.intersection(dish_words):
                    best_matches.append(dish_name)
            
            suggestions.extend(best_matches[:3])
        
        if suggestions:
            return False, f"Just to confirm—did you mean one of these: {', '.join(suggestions)}?"
    
    return True, response

def generate_response_simplified(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Generate response using simplified approach - AI handles dietary filtering directly
    """
    try:
        logger.info(f"SIMPLIFIED SYSTEM - Request from {req.client_id}: {req.message[:50]}...")
        
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
        business_type = restaurant_data.get('business_type', 'restaurant')
        menu_context = build_compact_menu_context(menu_items, business_type)
        
        # Get dish aliases block
        dish_aliases_block = get_dish_aliases_block()
        
        # Build system prompt - simpler, letting AI handle dietary filtering
        system_prompt = f"""You are Maria, a friendly server at {business_name}.

TOOL USE (AI decides)

If the guest asks for details ("more info", "details", "tell me about", "information", or says "yes" after you offered details): use get_dish_details(dish).

Always consider conversation history. If a specific dish is being discussed and the guest wants details, call get_dish_details for that dish.

If the guest asks by ingredient / category / name AND you need to search: use search_menu_items(search_term, search_type ∈ {{ingredient, category, name}}).

For greetings and small talk: respond naturally, no tools.

DIETARY REQUESTS (NO TOOL NEEDED)
When guests mention dietary needs (vegan, vegetarian, gluten-free, etc.), you MUST:
1. Look at the menu above - each dish shows [ingredients in brackets]
2. Check EVERY ingredient against the dietary requirement
3. Only suggest dishes where ALL ingredients meet the requirement

Dietary definitions:
• Vegan: NO animal products (no meat, fish, dairy, eggs, honey, gelatin, etc.)
  - "mozzarella", "parmesan", "cheese" = dairy = NOT vegan
  - "chicken", "beef", "fish", "anchovies" = animal = NOT vegan
• Vegetarian: No meat or fish (dairy and eggs ARE acceptable)
• Gluten-free: No wheat, barley, rye, pasta (unless specified gluten-free)
• Dairy-free: No milk, cheese, butter, cream, yogurt, or any dairy derivatives

IMPORTANT: Check the actual [ingredients] listed in the menu, not your assumptions.
Example: Caprese Skewers [mozzarella, cherry tomatoes, basil] = NOT vegan (contains mozzarella/dairy)

PARTIAL & MISSPELLINGS
• Normalize names (case/accents/spaces); tolerate common typos.
• If a single dish is clearly intended, call get_dish_details with the canonical dish.

CONTEXT STATE LINE (one hint may be appended to the user message)
Format: [Context: LastDish="{{dish}}"; LastCategory="{{category}}"; Candidates="{{dish1|dish2|dish3}}"; Diet="{{tag}}"]

ACTION RULES for the context line
• If LastDish is present and the user says "more / details / that / it / yes", call get_dish_details(dish=LastDish) and begin your reply with: "About {{LastDish}}…"
• If Candidates is present (≥2) and the user asks "more / details / that / it", do not choose; ask which one (list up to 3).
• If LastCategory is present (and no LastDish), you may use search_menu_items if needed.
• If Diet is present, keep that dietary restriction in mind for all recommendations.

STYLE & OUTPUT
• Be concise, warm, and accurate. Never invent items.
• After a tool returns, summarize the most relevant points and end with a helpful question.
• Do not print tool JSON or tags—use the tools interface only.

MENU (compact or compressed)
{menu_context}

CUSTOMER PROFILE
{customer_context}

DISH ALIASES (for canonicalization; keep short)
{dish_aliases_block}"""
        
        # Build system context
        system_context = {
            "business_name": business_name,
            "restaurant_name": business_name,
            "system_prompt": system_prompt
        }
        
        # Get recent chat history
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
        
        # Build conversation context
        chat_history = []
        for msg in reversed(recent_messages[1:]):
            if msg.sender_type == "client":
                chat_history.append(f"Customer: {msg.message}")
            elif msg.sender_type == "ai":
                chat_history.append(f"Maria: {msg.message}")
        
        conversation_context = "\n".join(chat_history) if chat_history else ""
        
        # Extract context state
        context_state = extract_context_state(recent_messages, menu_items, req.message)
        context_state_line = format_context_state_line(context_state)
        
        # Build prompt
        full_prompt = f"Customer: {req.message}"
        if context_state_line:
            full_prompt = f"{full_prompt} {context_state_line}"
        
        if conversation_context:
            full_prompt = f"Recent conversation:\n{conversation_context}\n\n{full_prompt}"
        
        # Determine decoding parameters
        message_lower = req.message.lower()
        tool_triggers = ["more info", "details", "tell me about", "information", "yes", "what", "which", "show me", "find", "search"]
        is_tool_likely = any(trigger in message_lower for trigger in tool_triggers)
        
        if is_tool_likely:
            decoding_params = {
                "temperature": 0.1,
                "top_p": 0.3,
                "max_tokens": 64
            }
        else:
            decoding_params = {
                "temperature": 0.4,
                "top_p": 1.0,
                "max_tokens": 200
            }
        
        # Send with tools
        response, used_tools, tool_call = send_to_mia_with_tools(
            full_prompt,
            AVAILABLE_TOOLS,
            system_context,
            decoding_params
        )
        
        # If tool was called, execute it
        if used_tools and tool_call:
            tool_name = tool_call.get("name")
            parameters = tool_call.get("parameters", {})
            
            logger.info(f"Executing tool: {tool_name} with params: {parameters}")
            tool_result = execute_tool(tool_name, parameters, menu_items)
            
            # Format result
            formatted_result = format_tool_result(tool_name, tool_result)
            
            follow_up_prompt = f"""Tool result: {formatted_result}

Customer's original question: {req.message}

Please provide a natural, friendly response based on this information."""
            
            # Final response with natural parameters
            final_decoding_params = {
                "temperature": 0.4,
                "top_p": 1.0,
                "max_tokens": 180
            }
            
            final_response, _, _ = send_to_mia_with_tools(
                follow_up_prompt,
                [],
                system_context,
                final_decoding_params
            )
            
            response = final_response
        
        # Optional output guard
        is_valid, corrected_response = check_menu_output_guard(response, menu_items)
        if not is_valid:
            response = corrected_response
        
        # Extract and update customer profile
        extracted_info = CustomerMemoryService.extract_customer_info(req.message)
        if extracted_info:
            CustomerMemoryService.update_customer_profile(
                db, req.client_id, req.restaurant_id, extracted_info
            )
        
        return ChatResponse(answer=response)
    
    except Exception as e:
        logger.error(f"Error in simplified service: {e}", exc_info=True)
        # Fall back to regular service
        return mia_chat_service_full_menu(req, db)

# Export the simplified function
mia_chat_service_full_menu_with_tools_simplified = generate_response_simplified