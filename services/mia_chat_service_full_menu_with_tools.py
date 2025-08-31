"""
MIA Chat Service - Full Menu with Tool Calling
Extends the existing full_menu service with tool/function calling capabilities
Falls back to full_menu behavior if tools aren't supported
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
    get_or_create_client
)
from services.customer_memory_service import CustomerMemoryService

logger = logging.getLogger(__name__)

# Tool definitions for MIA
AVAILABLE_TOOLS = [
    {
        "name": "get_dish_details",
        "description": "Get complete details about a specific dish including full description, all ingredients, preparation method, and allergens",
        "parameters": {
            "dish_name": {
                "type": "string",
                "description": "Name of the dish to get details for"
            }
        }
    },
    {
        "name": "search_menu_items",
        "description": "Search for menu items by ingredient, category, or name",
        "parameters": {
            "search_term": {
                "type": "string",
                "description": "What to search for (e.g., 'pasta', 'chicken', 'vegetarian')"
            },
            "search_type": {
                "type": "string",
                "enum": ["name", "ingredient", "category"],
                "description": "Type of search to perform (default: ingredient)"
            }
        }
    },
    {
        "name": "filter_by_dietary",
        "description": "Find dishes suitable for specific dietary restrictions",
        "parameters": {
            "restrictions": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of dietary restrictions (e.g., ['vegetarian', 'gluten-free', 'nut-free'])"
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
                "error": f"No dish found matching '{parameters.get('dish_name')}'"
            }
        
        elif tool_name == "search_menu_items":
            search_term = parameters.get("search_term", "").lower()
            search_type = parameters.get("search_type", "ingredient")
            results = []
            
            for item in menu_items:
                match = False
                
                if search_type == "name":
                    item_name = (item.get('dish') or item.get('name', '')).lower()
                    if search_term in item_name:
                        match = True
                
                elif search_type == "ingredient":
                    ingredients = [str(ing).lower() for ing in item.get('ingredients', [])]
                    if any(search_term in ing for ing in ingredients):
                        match = True
                
                elif search_type == "category":
                    category = (item.get('subcategory') or item.get('category', '')).lower()
                    if search_term in category:
                        match = True
                
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
            restrictions = [r.lower() for r in parameters.get("restrictions", [])]
            results = []
            
            for item in menu_items:
                allergens = [a.lower() for a in item.get('allergens', [])]
                ingredients = [i.lower() for i in item.get('ingredients', [])]
                
                # Check if item is suitable
                suitable = True
                
                for restriction in restrictions:
                    if restriction == "vegetarian":
                        meat_words = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'bacon', 'fish', 'seafood', 'shrimp', 'lobster']
                        if any(meat in ' '.join(ingredients) for meat in meat_words):
                            suitable = False
                            break
                    
                    elif restriction == "vegan":
                        animal_products = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'fish', 'seafood', 
                                         'cheese', 'milk', 'cream', 'butter', 'egg', 'honey']
                        if any(product in ' '.join(ingredients) for product in animal_products):
                            suitable = False
                            break
                    
                    elif restriction == "gluten-free" or restriction == "gluten free":
                        if "gluten" in allergens or any(gluten in ' '.join(ingredients) 
                                                       for gluten in ['pasta', 'bread', 'flour', 'wheat']):
                            suitable = False
                            break
                    
                    elif restriction == "nut-free" or restriction == "nut free":
                        if "nuts" in allergens or any(nut in ' '.join(ingredients) 
                                                     for nut in ['nut', 'almond', 'peanut', 'cashew', 'walnut']):
                            suitable = False
                            break
                    
                    elif restriction == "dairy-free" or restriction == "dairy free":
                        if "dairy" in allergens or any(dairy in ' '.join(ingredients) 
                                                      for dairy in ['milk', 'cheese', 'cream', 'butter', 'yogurt']):
                            suitable = False
                            break
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "brief": f"{item.get('dish', '')} - {item.get('price', '')}"
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results[:15],  # Limit to 15 items
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
    """Format tool result into natural language for MIA"""
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

def send_to_mia_with_tools(prompt: str, tools: List[Dict], context: Dict, 
                          max_rounds: int = 2) -> Tuple[str, bool]:
    """
    Send request to MIA with tool support
    Returns: (response_text, used_tools)
    """
    try:
        # Round 1: Initial request with tools
        request_data = {
            "message": prompt,
            "tools": tools,
            "context": context,
            "max_tokens": 300,
            "temperature": 0.7
        }
        
        logger.info(f"Sending to MIA with {len(tools)} tools available")
        
        # Use the hybrid service to communicate with MIA
        response = get_mia_response_hybrid(
            json.dumps(request_data),  # Convert to string as expected
            {"max_tokens": 300, "temperature": 0.7}
        )
        
        # Try to parse response as JSON (in case MIA returns structured data)
        try:
            response_data = json.loads(response)
            if response_data.get("tool_call"):
                logger.info(f"MIA requested tool: {response_data['tool_call']}")
                return response, True
            else:
                return response_data.get("response", response), False
        except:
            # Response is plain text, check for tool call patterns
            if "<tool_call>" in response or "TOOL_CALL:" in response:
                logger.info("Detected tool call pattern in response")
                return response, True
            
            # No tool call, return response as-is
            return response, False
    
    except Exception as e:
        logger.error(f"Error in tool communication: {e}")
        # Fall back to response without tools
        return get_mia_response_hybrid(prompt, {"max_tokens": 300, "temperature": 0.7}), False

def generate_response_full_menu_with_tools(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Generate response using full menu context with optional tool calling
    Falls back to regular full_menu if tools aren't used
    """
    try:
        logger.info(f"FULL MENU WITH TOOLS - Request from {req.client_id}: {req.message[:50]}...")
        
        # Get restaurant and menu data
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant or not restaurant.data:
            return ChatResponse(answer="I'm sorry, but I couldn't find the restaurant information.")
        
        menu_items = restaurant.data.get('menu', [])
        business_name = restaurant.data.get('restaurant_name', req.restaurant_id)
        business_type = restaurant.data.get('business_type', 'restaurant')
        
        # Always use tools - let AI decide when to use them
        logger.info("FULL MENU WITH TOOLS - AI will decide when to use tools")
        
        # Get customer profile for context
        client_id_str = str(req.client_id)
        customer_profile = db.query(models.CustomerProfile).filter(
            models.CustomerProfile.client_id == client_id_str,
            models.CustomerProfile.restaurant_id == req.restaurant_id
        ).first()
        customer_context = CustomerMemoryService.get_customer_context(customer_profile)
        
        # Get recent chat history for better context
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(6).all()
        
        # Build conversation history
        chat_history = []
        for msg in reversed(recent_messages[1:]):  # Skip current message
            if msg.sender_type == "client":
                chat_history.append(f"Customer: {msg.message}")
            elif msg.sender_type == "ai":
                chat_history.append(f"Maria: {msg.message}")
        
        # Prepare minimal context for tool-based approach
        system_context = {
            "restaurant_name": business_name,
            "business_type": business_type,
            "system_prompt": f"""You are Maria, a friendly server at {business_name}.
Be warm, helpful, and natural in your responses.

CRITICAL RULES - FOLLOW EXACTLY:
1. When a customer says "I want [ingredient/type]" → IMMEDIATELY use search_menu_items tool
2. DO NOT ask "Would you like to see options?" → Just show them
3. DO NOT ask "Any specific type?" → Search first, show all options
4. After showing options, THEN ask preferences
5. DO NOT greet again if you already greeted in this conversation
6. Remember the ENTIRE conversation - if customer mentioned something earlier, remember it

WRONG: "Would you like to see some meat dishes?"
RIGHT: *uses search_menu_items for "meat"* "Here are our meat dishes: [list]"

WRONG: "Hello again!" (if already greeted)
RIGHT: Jump straight to answering their question

You have access to tools that can help you provide accurate information:
- get_dish_details: Get complete details about a specific dish
- search_menu_items: Find dishes with specific ingredients (USE THIS when customers mention any ingredient)
- filter_by_dietary: Find dishes suitable for dietary restrictions

Examples:
- Customer: "I want fish" → Use search_menu_items("fish") → Show results
- Customer: "I want meat" → Use search_menu_items("meat") → Show results  
- Customer: "Hello" → Greet normally, no tools needed

Remember: ACTION FIRST, QUESTIONS LATER!

{customer_context}"""
        }
        
        # Prepare the prompt with conversation history
        conversation_context = "\n".join(chat_history) if chat_history else ""
        
        full_prompt = f"""{system_context['system_prompt']}

{f"Recent conversation:{chr(10)}{conversation_context}{chr(10)}" if conversation_context else ""}
Customer: {req.message}
Maria:"""
        
        # Try to use tools
        logger.info(f"Sending prompt with {len(AVAILABLE_TOOLS)} tools: {[t['name'] for t in AVAILABLE_TOOLS]}")
        response, used_tools = send_to_mia_with_tools(
            full_prompt,
            AVAILABLE_TOOLS,
            system_context,
            max_rounds=2
        )
        logger.info(f"Response from MIA, used_tools={used_tools}")
        
        # If tools were requested, execute them
        if used_tools and ("<tool_call>" in response or "TOOL_CALL:" in response):
            logger.info("Processing tool calls from MIA")
            
            # Extract tool call (basic pattern matching)
            tool_call = None
            if "<tool_call>" in response:
                start = response.find("<tool_call>") + len("<tool_call>")
                end = response.find("</tool_call>")
                if end > start:
                    try:
                        tool_call = json.loads(response[start:end].strip())
                    except:
                        logger.error("Failed to parse tool call")
            elif "TOOL_CALL:" in response:
                start = response.find("TOOL_CALL:") + len("TOOL_CALL:")
                try:
                    # Find the JSON part
                    json_start = response[start:].find("{")
                    if json_start >= 0:
                        json_str = response[start + json_start:].split("\n")[0]
                        tool_call = json.loads(json_str)
                except:
                    logger.error("Failed to parse TOOL_CALL format")
            
            if tool_call:
                # Execute the tool
                tool_name = tool_call.get("name")
                parameters = tool_call.get("parameters", {})
                
                logger.info(f"Executing tool: {tool_name} with params: {parameters}")
                tool_result = execute_tool(tool_name, parameters, menu_items)
                
                # Format result and send back to MIA
                formatted_result = format_tool_result(tool_name, tool_result)
                
                # Second round: Send tool results back to MIA
                follow_up_prompt = f"""{system_context['system_prompt']}

Customer: {req.message}

Tool Result:
{formatted_result}

Now provide a natural, friendly response to the customer using this information:
Assistant:"""
                
                # Get final response
                final_response = get_mia_response_hybrid(
                    follow_up_prompt,
                    {"max_tokens": 300, "temperature": 0.7}
                )
                
                response = final_response
        
        # Clean up any remaining tool syntax from response
        response = response.replace("<tool_call>", "").replace("</tool_call>", "")
        response = response.replace("TOOL_CALL:", "")
        
        # Remove "Assistant:" or "Maria:" prefix if model adds it
        response = response.strip()
        if response.startswith("Assistant:"):
            response = response[10:].strip()
        elif response.startswith("Maria:"):
            response = response[6:].strip()
        
        # Get or create client first
        get_or_create_client(db, req.client_id, req.restaurant_id)
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=response.strip()
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(answer=response.strip())
    
    except Exception as e:
        logger.error(f"Error in full menu with tools service: {e}", exc_info=True)
        # Fall back to regular full_menu on any error
        logger.info("Falling back to standard full_menu due to error")
        return mia_chat_service_full_menu(req, db)