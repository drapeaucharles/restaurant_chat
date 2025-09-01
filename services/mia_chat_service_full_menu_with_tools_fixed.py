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
            "description": "Use this when customer asks for 'more info', 'details', 'tell me about' a specific dish, OR when they say 'yes' to your offer for more information. IMPORTANT: Check conversation history to identify which dish they're referring to. Returns complete details including full description, all ingredients, preparation method, and allergens",
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
            "description": "Search for menu items by ingredient, category, or name",
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
            "description": "Find dishes suitable for specific dietary restrictions",
            "parameters": {
                "type": "object",
                "properties": {
                    "restrictions": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "List of dietary restrictions (e.g., ['vegetarian', 'gluten-free', 'nut-free'])"
                    }
                },
                "required": ["restrictions"]
            }
        }
    }
]

def execute_tool(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool and return results"""
    try:
        if tool_name == "get_dish_details":
            dish_name = parameters.get("dish_name", "").lower()
            
            # Find exact or partial match
            for item in menu_items:
                item_name = (item.get('dish') or item.get('name', '')).lower()
                if dish_name in item_name or item_name in dish_name:
                    # Build detailed response
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
            
            return {
                "success": False,
                "error": f"Dish '{dish_name}' not found"
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
                allergens = [a.lower() for a in item.get('allergens', [])]
                ingredients_str = ' '.join(item.get('ingredients', [])).lower()
                
                for restriction in restrictions:
                    restriction_lower = restriction.lower()
                    
                    if restriction_lower == "vegetarian":
                        meat_words = ['meat', 'chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood', 'shrimp']
                        if any(word in ingredients_str for word in meat_words):
                            suitable = False
                    
                    elif restriction_lower == "vegan":
                        non_vegan = ['meat', 'chicken', 'beef', 'fish', 'egg', 'dairy', 'cheese', 'milk', 'cream', 'butter']
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
        # Prepare the chat request with tools
        request_data = {
            "message": prompt,
            "context": context,
            "tools": tools,
            "tool_choice": "auto",
            "max_tokens": 300,
            "temperature": 0.7
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
        
        # Build system context with customer info
        system_context = {
            "business_name": business_name,
            "restaurant_name": business_name,
            "system_prompt": f"""You are Maria, a friendly server at {business_name}.

IMPORTANT TOOL USAGE RULES:
1. When customer asks for "more info", "details", "tell me about", "information", or says "yes" to a request for details → USE get_dish_details tool
2. ALWAYS check the conversation history - if discussing a specific dish and customer wants details, use get_dish_details with that dish
3. When customer asks what dishes contain an ingredient (fish, chicken, vegetarian, etc) → USE search_menu_items tool
4. When customer asks about dietary restrictions → USE filter_by_dietary tool
5. For greetings and general chat → respond naturally without tools
6. If a tool returns "not found" or the customer asks about something not on our menu → politely inform them and suggest alternatives

CONTEXT AWARENESS: Always consider the previous messages in the conversation when interpreting requests.

NEVER make up dish details - always use tools to get accurate information from our database. If an item isn't found, be honest about it.

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
        
        # Build prompt with enhanced context
        # If the message is ambiguous, add context hint
        ambiguous_phrases = ["yes", "tell me more", "details", "more info", "information", "about that", "about it"]
        is_ambiguous = any(phrase in req.message.lower() for phrase in ambiguous_phrases)
        
        if is_ambiguous and recent_messages:
            # Find the last mentioned dish by checking raw messages in reverse order
            last_dish_mentioned = None
            # Check last 10 messages, prioritizing most recent customer messages
            for msg in recent_messages[:10]:  # recent_messages is already in desc order
                if msg.sender_type == "client":
                    msg_lower = msg.message.lower()
                    # Check against menu items for exact matches first
                    for item in menu_items:
                        item_name = (item.get('dish') or item.get('name', '')).lower()
                        # Check if dish name appears in customer message
                        if item_name and len(item_name) > 3:  # Skip very short names
                            # Check for exact word match or partial match
                            if item_name in msg_lower or any(word in msg_lower for word in item_name.split()):
                                last_dish_mentioned = item_name
                                break
                    
                    # If no exact menu match, check common food words
                    if not last_dish_mentioned:
                        for word in ["tuna", "salmon", "scallops", "pasta", "steak", "chicken", "lobster", "shrimp", "fish", "pizza", "burger", "salad", "soup"]:
                            if word in msg_lower:
                                last_dish_mentioned = word
                                break
                
                if last_dish_mentioned:
                    break
            
            if last_dish_mentioned:
                full_prompt = f"""Customer: {req.message} [Context: Customer is asking about {last_dish_mentioned}]"""
            else:
                full_prompt = f"""Customer: {req.message}"""
        else:
            full_prompt = f"""Customer: {req.message}"""
        
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