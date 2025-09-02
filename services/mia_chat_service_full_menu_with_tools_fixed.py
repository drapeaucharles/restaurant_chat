"""
MIA Chat Service - Full Menu with Tool Calling (Fixed)
Uses proper OpenAI tool format instead of text conversion
"""
import json
import time
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse

# Import the existing full_menu service functions
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

# Tool definitions for MIA (OpenAI format)
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dish_details",
            "description": "Authoritative dish explainer. Input: dish_name (string). Returns the official description and ingredient list exactly as stored. Use only when the guest asks for \"more info / details / tell me about\" a specific dish, or when you need to cite one concrete conflicting ingredient.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish_name": {
                        "type": "string",
                        "description": "Name of the dish to get details for"
                    }
                },
                "required": ["dish_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_menu_items",
            "description": "Find menu items by ingredient, category, or name. Use to narrow results after filtering by diet/allergy, or to resolve partial names. Never use search alone for diet/allergy safety.",
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
                        "description": "Type of search to perform (default: ingredient)"
                    }
                },
                "required": ["search_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_dietary",
            "description": "Authoritative dietary filter based on database toggles and tags (is_vegan, is_vegetarian, is_gluten_free, is_dairy_free, is_nut_free, dietary_tags like keto-friendly, paleo). Input: restrictions (array of normalized strings). Output: only dishes that satisfy all restrictions. Must be called whenever a diet or allergy is mentioned. Do not recommend any item not returned by this tool.",
            "parameters": {
                "type": "object",
                "properties": {
                    "restrictions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Normalized strings: vegan, vegetarian, gluten-free, dairy-free, nut-free, keto-friendly, paleo. Multiple restrictions allowed."
                    }
                },
                "required": ["restrictions"]
            }
        }
    }
]

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

def execute_tool(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool and return results"""
    try:
        if tool_name == "get_dish_details":
            requested_dish = parameters.get("dish_name", "")
            requested_lower = requested_dish.lower().strip()
            
            # 1. Try exact match first (case-insensitive)
            for item in menu_items:
                item_name = item.get('dish') or item.get('name', '')
                if requested_lower == item_name.lower():
                    return build_dish_details_response(item)
            
            # 2. Try fuzzy matching with normalization
            best_match = None
            best_score = 0
            
            # Remove common cooking prefixes that might differ
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
                
                # Check if main ingredient matches
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
            
            # 3. Return best match if confidence is high enough
            if best_match and best_score > 0.7:
                return build_dish_details_response(best_match[0])
            
            # 4. No good match found
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
                "items": results[:15]  # Limit to 15 items
            }
        
        elif tool_name == "filter_by_dietary":
            restrictions = parameters.get("restrictions", [])
            results = []
            
            for item in menu_items:
                suitable = True
                
                # Check if item has dietary fields in database
                has_dietary_fields = any(
                    field in item for field in 
                    ['is_vegan', 'is_vegetarian', 'is_gluten_free', 'is_dairy_free', 'is_nut_free']
                )
                
                for restriction in restrictions:
                    restriction_lower = restriction.lower()
                    
                    if has_dietary_fields:
                        # Use database fields for accurate filtering
                        if restriction_lower == "vegan" and not item.get('is_vegan'):
                            suitable = False
                        elif restriction_lower == "vegetarian" and not item.get('is_vegetarian'):
                            suitable = False
                        elif "gluten" in restriction_lower and not item.get('is_gluten_free'):
                            suitable = False
                        elif "dairy" in restriction_lower and not item.get('is_dairy_free'):
                            suitable = False
                        elif "nut" in restriction_lower and not item.get('is_nut_free'):
                            suitable = False
                        # Check dietary tags for other restrictions
                        elif restriction_lower in ["keto", "paleo", "halal", "kosher", "keto-friendly"]:
                            dietary_tags = item.get('dietary_tags', [])
                            # Handle both 'keto' and 'keto-friendly' formats
                            if restriction_lower == "keto-friendly" or restriction_lower == "keto":
                                if not any(tag in ["keto", "keto-friendly"] for tag in dietary_tags):
                                    suitable = False
                            elif restriction_lower not in dietary_tags:
                                suitable = False
                    else:
                        # Fallback to pattern matching for items without dietary fields
                        allergens = [a.lower() for a in item.get('allergens', [])]
                        ingredients_str = ' '.join(item.get('ingredients', [])).lower()
                        
                        if restriction_lower == "vegetarian":
                            meat_words = ['meat', 'chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood', 'shrimp', 
                                          'bacon', 'prosciutto', 'anchovies', 'tuna', 'salmon']
                            if any(word in ingredients_str for word in meat_words):
                                suitable = False
                        
                        elif restriction_lower == "vegan":
                            non_vegan = ['meat', 'chicken', 'beef', 'fish', 'egg', 'dairy', 'cheese', 'milk', 
                                         'cream', 'butter', 'mozzarella', 'parmesan', 'ricotta', 'mascarpone']
                            if any(word in ingredients_str for word in non_vegan):
                                suitable = False
                        
                        elif "gluten" in restriction_lower:
                            if "gluten" in allergens or "wheat" in allergens:
                                suitable = False
                        
                        elif "nut" in restriction_lower:
                            if any("nut" in a for a in allergens):
                                suitable = False
                        
                        elif "dairy" in restriction_lower:
                            if "dairy" in allergens or "lactose" in allergens:
                                suitable = False
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "brief": f"{item.get('dish', '')} - {item.get('price', '')}"
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results[:15],
                "restrictions_applied": restrictions
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

def calculate_match_confidence(query: str, item_name: str) -> float:
    """Calculate confidence score for matching query to item name"""
    query_lower = query.lower().strip()
    item_lower = item_name.lower().strip()
    
    # Exact match
    if query_lower == item_lower:
        return 1.0
    
    # Contains full query
    if query_lower in item_lower:
        return 0.9
    
    # Item name contains all words from query
    query_words = set(query_lower.split())
    item_words = set(item_lower.split())
    if query_words.issubset(item_words):
        return 0.85
    
    # Partial word matches
    matching_words = query_words.intersection(item_words)
    if matching_words:
        return len(matching_words) / len(query_words) * 0.8
    
    # Check if query is substring of any word in item
    for item_word in item_words:
        if query_lower in item_word:
            return 0.7
    
    return 0.0

def find_menu_matches(query: str, menu_items: List[Dict]) -> Tuple[List[Dict], str]:
    """
    Find matching menu items and determine match type
    Returns: (matches, hint_type)
    """
    query_lower = query.lower().strip()
    matches = []
    category_matches = []
    
    # First check if query matches a category
    for item in menu_items:
        item_name = item.get('dish') or item.get('name', '')
        category = item.get('category', '').lower()
        subcategory = item.get('subcategory', '').lower()
        
        # Check category match
        if query_lower == category or query_lower == subcategory:
            category_matches.append({
                'item': item,
                'name': item_name,
                'confidence': 1.0,  # Exact category match
                'id': f"dish:{item_name.lower().replace(' ', '_')}"
            })
        
        # Check dish name match
        if item_name:
            confidence = calculate_match_confidence(query, item_name)
            if confidence > 0.6:  # Threshold for considering a match
                matches.append({
                    'item': item,
                    'name': item_name,
                    'confidence': confidence,
                    'id': f"dish:{item_name.lower().replace(' ', '_')}"
                })
    
    # If we found category matches, use those
    if category_matches:
        return category_matches, "category"
    
    # Sort by confidence
    matches.sort(key=lambda x: x['confidence'], reverse=True)
    
    # Determine hint type
    if not matches:
        return [], "none"
    elif len(matches) == 1 and matches[0]['confidence'] > 0.85:
        return matches[:1], "single"
    elif len(matches) == 1:
        return matches[:1], "partial"
    else:
        # Check if all matches are same category
        categories = set(m['item'].get('category', '') for m in matches)
        if len(categories) == 1 and categories != {''}:
            return matches, "category"
        return matches, "multi"

def generate_simple_context(query: str, menu_items: List[Dict], last_dish_mentioned: Optional[str] = None) -> str:
    """Generate simple context line for AI"""
    query_lower = query.lower().strip()
    
    # Check if this is an ambiguous reference
    ambiguous_phrases = ["yes", "tell me more", "details", "more info", "information", "about that", "about it", "it", "that", "this"]
    is_ambiguous = any(phrase in query_lower for phrase in ambiguous_phrases)
    
    # If ambiguous and we know what dish was last discussed
    if is_ambiguous and last_dish_mentioned:
        return f'[Context: Last discussed "{last_dish_mentioned}"]'
    
    # Find menu matches
    matches, match_type = find_menu_matches(query, menu_items)
    
    # No matches found
    if match_type == "none":
        # Check if it might be a category
        category_keywords = ["pasta", "pizza", "seafood", "salad", "appetizer", "dessert", "soup", "sandwich"]
        if query_lower in category_keywords:
            # Find all items in this category
            category_items = []
            for item in menu_items:
                if query_lower in (item.get('category', '').lower() + ' ' + item.get('subcategory', '').lower()):
                    category_items.append(item.get('dish') or item.get('name', ''))
            
            if category_items:
                items_str = " | ".join(category_items[:5])
                return f'[Context: Category: {query} → {items_str}]'
        
        # Try to find similar items
        suggestions = []
        for item in menu_items:
            item_name = (item.get('dish') or item.get('name', '')).lower()
            if any(word in item_name for word in query_lower.split() if len(word) > 3):
                suggestions.append(item.get('dish') or item.get('name', ''))
        
        if suggestions:
            suggest_str = " | ".join(suggestions[:2])
            return f'[Context: No match for "{query}" (suggest: {suggest_str})]'
        else:
            return ''  # No context needed
    
    # Single match found
    elif match_type == "single" and matches[0]['confidence'] > 0.85:
        return f'[Context: Single "{matches[0]["name"]}"]'
    
    # Partial match
    elif match_type == "partial":
        return f'[Context: Partial "{query}"]'
    
    # Multiple matches
    elif match_type == "multi" or (match_type == "category" and len(matches) > 1):
        options = " | ".join(m['name'] for m in matches[:3])
        return f'[Context: Options: {options}]'
    
    # Category with items
    elif match_type == "category":
        category = matches[0]['item'].get('category', 'items')
        items = " | ".join(m['name'] for m in matches[:5])
        return f'[Context: Category: {category} → {items}]'
    
    return ''  # No special context needed

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
    
    elif tool_name == "filter_by_dietary":
        items = result.get("items", [])
        restrictions = result.get("restrictions_applied", [])
        
        if not items:
            return f"I couldn't find any items suitable for {', '.join(restrictions)} dietary restrictions."
        
        response = f"Here are {len(items)} options suitable for {', '.join(restrictions)}:\n"
        response += "\n".join([f"- {item['brief']}" for item in items])
        return response
    
    return str(result)

def send_to_mia_with_tools(prompt: str, tools: List[Dict], context: Dict) -> Tuple[str, bool, Optional[Dict]]:
    """
    Send request to MIA with proper tool support
    Returns: (response_text, used_tools, tool_call_info)
    """
    try:
        # Prepare the chat request with tools - using recommended settings
        request_data = {
            "message": prompt,
            "context": context,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 300,
            "temperature": 0.35,  # Lower temperature for more consistent tool usage
            "top_p": 1.0
        }
        
        logger.info(f"Sending to MIA with {len(tools)} tools")
        
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
        return get_mia_response_hybrid(prompt, {"max_tokens": 300, "temperature": 0.7}), False, None

def generate_response_full_menu_with_tools(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Generate response using full menu context with proper tool calling
    """
    try:
        logger.info(f"FULL MENU WITH TOOLS (Fixed) - Request from {req.client_id}: {req.message[:50]}...")
        
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
        
        # Get customer profile first
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
        
        # Build system context with customer info and menu
        system_context = {
            "business_name": business_name,
            "restaurant_name": business_name,
            "system_prompt": f"""You are Maria, a friendly but precise server at {business_name}. You have access to three tools: get_dish_details(dish_name), search_menu_items(search_term, search_type ∈ {{ingredient, category, name}}), and filter_by_dietary(restrictions: array of strings). Be concise, warm, and accurate. Never invent items or ingredients.

Critical dietary and allergy policy (highest priority)

1. Mandatory tool call
If the guest message or Context Line mentions any diet/allergy (examples: vegan, vegetarian, gluten-free, dairy-free, nut-free, keto-friendly, paleo), you must call filter_by_dietary first with restrictions as an array of normalized strings. Your recommendations must be a subset of this tool's returned items. Do not guess from dish names.

2. Category/name/ingredient under a diet (CRITICAL - TWO TOOLS REQUIRED)
If the guest asks for both a diet AND a category (e.g., "vegan appetizers", "gluten-free pasta", "vegetarian mains"):
a) FIRST call filter_by_dietary with the diet restriction.
b) THEN call search_menu_items with the category/ingredient/name.
c) Recommend ONLY items that appear in BOTH results (the intersection).
d) If no items match both criteria, say so clearly (e.g., "We don't have any default vegan appetizers").

3. Yes/No checks about a specific dish
For questions like "Is Caprese vegan/dairy-free/gluten-free?":
a) Call filter_by_dietary with the restriction(s).
b) If the dish is included in the tool's output, answer "Yes".
c) If it is not included, answer "No" and, if helpful, call get_dish_details to name one concrete conflicting ingredient exactly as listed (e.g., mozzarella is dairy). Never speculate beyond the stored ingredients.

4. Empty results
If filter_by_dietary returns no items (or the category/name intersection is empty), clearly say no default items meet the requirement. Offer clearly labeled customizations (e.g., "Bruschetta without mozzarella") and ask the guest to confirm. Do not present a customization as inherently compliant; label it as a customization.

5. Context persistence
If Diet appears in the Context Line or the guest states a diet, keep applying it to every turn until the guest cancels or changes it. If they change diets, acknowledge and switch immediately.

Context Line behavior
• If LastDish is set and the guest says "more / details / that / it / yes", call get_dish_details for LastDish and begin with: About {{LastDish}}…
• If Candidates (≥2) are shown and the guest says "that / it / more", ask which one (list up to three) before calling tools.
• If a category is shown, you may call search_menu_items(category) to present up to five items, but still obey the dietary policy above.

Style and outputs
• Keep it short and helpful. After tool calls, summarize clearly (max five items) and end with a helpful question.
• Do not print tool JSON or internal data; speak naturally.
• When in doubt (hidden ingredients, shared fryers, cross-contact), say so and offer to check with the kitchen.

Diet definitions (for wording; the database is the source of truth)
Vegan: no animal products (meat, fish, shellfish, dairy, eggs, honey, gelatin, lard).
Vegetarian: no meat, fish, shellfish (dairy and eggs are acceptable).
Gluten-free: no wheat, barley, rye, conventional pasta/bread/flour unless explicitly gluten-free.
Dairy-free: no milk, cheese, butter, cream, yogurt, whey, mascarpone, etc.

Normalization to apply before calling filter_by_dietary:
vegan → vegan
vegetarian → vegetarian
gluten free / gluten-free / gf → gluten-free
dairy free / dairy-free / lactose free → dairy-free
nut free / nut-free → nut-free
keto / keto friendly / keto-friendly → keto-friendly
paleo → paleo

Micro-examples:
Guest: "vegan appetizers please"
Actions: 1) filter_by_dietary(["vegan"]) 2) search_menu_items("appetizers", "category") 3) Show ONLY intersection

Guest: "gluten-free seafood"  
Actions: 1) filter_by_dietary(["gluten-free"]) 2) search_menu_items("seafood", "category") 3) Show ONLY intersection

Absolute rules
• Never recommend any dish that is not included in filter_by_dietary results for the active restrictions.
• Never rely on dish names to infer suitability; use the tool output and official ingredients.
• If ingredients are missing for a dish, do not recommend it for restricted diets; offer to check with the kitchen first.
• Keep the active diet in effect until canceled.

{menu_context}

Customer Profile:
{customer_context}"""
        }
        
        # Get recent chat history for context
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
        
        # Build conversation context
        chat_history = []
        for msg in reversed(recent_messages[1:]):  # Skip current message
            if msg.sender_type == "client":
                chat_history.append(f"Customer: {msg.message}")
            elif msg.sender_type == "ai":
                chat_history.append(f"Maria: {msg.message}")
        
        conversation_context = "\n".join(chat_history) if chat_history else ""
        
        # Build prompt with structured hints
        # Find last mentioned food topic from recent messages
        last_topic = None
        for msg in recent_messages[:10]:  # recent_messages is already in desc order
            if msg.sender_type == "client":
                msg_lower = msg.message.lower()
                # Check against menu items
                for item in menu_items:
                    item_name = (item.get('dish') or item.get('name', '')).lower()
                    if item_name and len(item_name) > 3:
                        if item_name in msg_lower or any(word in msg_lower for word in item_name.split()):
                            last_topic = item_name
                            break
                
                # Check categories
                if not last_topic:
                    categories = set(item.get('category', '').lower() for item in menu_items)
                    for category in categories:
                        if category and category in msg_lower:
                            last_topic = category
                            break
                
                # Check common food words if no menu match
                if not last_topic:
                    for word in ["tuna", "salmon", "scallops", "pasta", "steak", "chicken", "lobster", "shrimp", "fish", "pizza", "burger", "salad", "soup"]:
                        if word in msg_lower:
                            last_topic = word
                            break
                
                if last_topic:
                    break
        
        # Find last mentioned dish from AI responses (what was actually discussed)
        last_dish_mentioned = None
        
        # Look through recent messages for actual dish names mentioned by AI
        for msg in recent_messages[:10]:  # most recent first
            if msg.sender_type == "ai":
                # Check if AI mentioned specific dishes
                for item in menu_items:
                    dish_name = item.get('dish') or item.get('name', '')
                    if dish_name and dish_name in msg.message:
                        last_dish_mentioned = dish_name
                        break
                
                if last_dish_mentioned:
                    break
        
        # Generate simple context line
        context = generate_simple_context(req.message, menu_items, last_dish_mentioned)
        full_prompt = f"""Customer: {req.message} {context}""" if context else f"""Customer: {req.message}"""
        
        if conversation_context:
            full_prompt = f"Recent conversation:\n{conversation_context}\n\n{full_prompt}"
        
        # Send with tools
        response, used_tools, tool_call = send_to_mia_with_tools(
            full_prompt,
            AVAILABLE_TOOLS,
            system_context
        )
        
        # If tool was called, execute it
        if used_tools and tool_call:
            tool_name = tool_call.get("name")
            parameters = tool_call.get("parameters", {})
            
            logger.info(f"Executing tool: {tool_name} with params: {parameters}")
            tool_result = execute_tool(tool_name, parameters, menu_items)
            
            # Format result
            formatted_result = format_tool_result(tool_name, tool_result)
            
            # Send tool result back to MIA for final response
            follow_up_prompt = f"""Tool result: {formatted_result}

Customer's original question: {req.message}

Please provide a natural, friendly response based on this information."""
            
            final_response, _, _ = send_to_mia_with_tools(
                follow_up_prompt,
                [],  # No tools for follow-up
                system_context
            )
            
            response = final_response
        
        # Extract and update customer profile if needed
        extracted_info = CustomerMemoryService.extract_customer_info(req.message)
        if extracted_info:
            CustomerMemoryService.update_customer_profile(
                db, req.client_id, req.restaurant_id, extracted_info
            )
        
        return ChatResponse(answer=response)
    
    except Exception as e:
        logger.error(f"Error in tool service: {e}", exc_info=True)
        # Fall back to regular service
        return mia_chat_service_full_menu(req, db)

# Export the fixed function
mia_chat_service_full_menu_with_tools_fixed = generate_response_full_menu_with_tools