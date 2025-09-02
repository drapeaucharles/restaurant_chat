"""
MIA Chat Service - AI-Powered Dietary Classification
Uses LLM intelligence for dietary filtering instead of hardcoded lists
"""
import json
import time
import logging
from typing import Dict, List, Optional, Tuple, Set
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse

# Import base functionality
from services.mia_chat_service_full_menu_with_tools_upgraded import (
    AVAILABLE_TOOLS,
    DISH_ALIASES,
    get_dish_aliases_block,
    build_dish_details_response,
    canonicalize_dish_name,
    extract_context_state,
    format_context_state_line,
    format_tool_result,
    send_to_mia_with_tools,
    check_menu_output_guard,
    CustomerMemoryService,
    build_compact_menu_context,
    MIA_BACKEND_URL,
    requests
)

logger = logging.getLogger(__name__)

def execute_tool_ai_dietary(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool and return results - using AI for dietary classification"""
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
        
        elif tool_name == "filter_by_dietary":
            diet = parameters.get("diet", "").lower()
            
            # Since AI already has the full menu, just return a confirmation
            # The AI will do the filtering based on its knowledge
            return {
                "success": True,
                "diet_requested": diet,
                "message": f"I'll analyze our menu for {diet} options using my knowledge of dietary requirements."
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

def format_tool_result_ai_dietary(tool_name: str, result: Dict) -> str:
    """Format tool result into natural language - special handling for AI dietary filtering"""
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
        diet = result.get("diet_requested", "")
        return result.get("message", f"Analyzing menu for {diet} options...")
    
    return str(result)

def generate_response_ai_dietary(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Generate response using AI-powered dietary classification
    """
    try:
        logger.info(f"AI DIETARY SYSTEM - Request from {req.client_id}: {req.message[:50]}...")
        
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
        
        # Build system prompt with AI dietary classification emphasis
        system_prompt = f"""You are Maria, a friendly server at {business_name}.

TOOL USE (AI decides)

If the guest asks for details ("more info", "details", "tell me about", "information", or says "yes" after you offered details): use get_dish_details(dish).

Always consider conversation history. If a specific dish is being discussed and the guest wants details, call get_dish_details for that dish.

If the guest asks by ingredient / category / name ("fish", "chicken", "vegetarian", "pasta", "pizza", "seafood"): use search_menu_items(search_term, search_type ∈ {{ingredient, category, name}}).

If the guest asks by dietary need: use filter_by_dietary(diet).

For greetings and small talk: respond naturally, no tools.

DIETARY FILTERING WITH AI INTELLIGENCE
When you call filter_by_dietary, it's just a signal that the customer needs dietary filtering. 
You already have the full menu with all ingredients in your context above.
After calling the tool, YOU must:
• Analyze each dish in our menu using your knowledge
• Vegan: No animal products (meat, fish, dairy, eggs, honey, gelatin, etc.)
• Vegetarian: No meat or fish (dairy and eggs are acceptable)
• Gluten-free: No wheat, barley, rye, or gluten-containing ingredients
• Dairy-free: No milk, cheese, butter, cream, or dairy derivatives
• Use your comprehensive knowledge of ingredients, including uncommon ones (e.g., "guanciale" is pork, "mascarpone" is dairy)

Only suggest dishes that are truly suitable - be strict in your analysis.

PARTIAL & MISSPELLINGS
• Normalize names (case/accents/spaces); tolerate common typos (e.g., "fetuticini carbonera" → "Spaghetti Carbonara").
• If a single dish is clearly intended, call get_dish_details with the canonical dish and add a soft confirmation.
• If unsure, first call search_menu_items(search_type="name"); if it returns one plausible dish, then call get_dish_details. If multiple, ask one brief clarifying question (no tool yet).

CONTEXT STATE LINE (one hint may be appended to the user message)
Format (one line, keys optional; include only what you have):
[Context: LastDish="{{dish}}"; LastCategory="{{category}}"; Candidates="{{dish1|dish2|dish3}}"; Diet="{{tag}}"]

ACTION RULES for the context line
• If LastDish is present and the user says "more / details / that / it / yes", call get_dish_details(dish=LastDish) and begin your reply with: "About {{LastDish}}…"
• If Candidates is present (≥2) and the user asks "more / details / that / it", do not choose; ask which one (list up to 3).
• If LastCategory is present (and no LastDish), call search_menu_items(search_type="category", search_term=LastCategory) and then ask the guest to pick.
• If Diet is present, always call filter_by_dietary(diet=Diet) before recommending anything. Analyze the results using your knowledge before suggesting items.

STYLE & OUTPUT
• Be concise, warm, and accurate. Never invent items—use tools.
• After a tool returns, summarize the most relevant points (≤5 items or 2–3 sentences) and end with a helpful question.
• Do not print tool JSON or tags—use the tools interface only.
• If unsure, ask one short clarification.

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
        tool_triggers = ["more info", "details", "tell me about", "information", "yes", "what", "which", "show me", "find", "search", "vegan", "vegetarian", "gluten", "dairy"]
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
            tool_result = execute_tool_ai_dietary(tool_name, parameters, menu_items)
            
            # Format result
            formatted_result = format_tool_result_ai_dietary(tool_name, tool_result)
            
            # For dietary filtering, enhance the follow-up prompt
            if tool_name == "filter_by_dietary":
                diet = tool_result.get("diet_requested", "")
                follow_up_prompt = f"""The customer asked: {req.message}

Now analyze our menu (which you have in your context) and identify dishes suitable for a {diet} diet.
Use your knowledge to understand each ingredient - be strict and accurate.
Only recommend dishes that are truly {diet}.
Provide a natural, friendly response listing the suitable options with brief explanations."""
            else:
                follow_up_prompt = f"""Tool result: {formatted_result}

Customer's original question: {req.message}

Please provide a natural, friendly response based on this information."""
            
            # Final response with natural parameters
            final_decoding_params = {
                "temperature": 0.4,
                "top_p": 1.0,
                "max_tokens": 250  # Slightly more for dietary explanations
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
        logger.error(f"Error in AI dietary service: {e}", exc_info=True)
        # Fall back to regular service
        from services.mia_chat_service_full_menu import mia_chat_service_full_menu
        return mia_chat_service_full_menu(req, db)

# Export the AI dietary function
mia_chat_service_full_menu_with_tools_ai_dietary = generate_response_ai_dietary