"""
MIA Chat Service with Internal Tool Flow
Handles tool discovery and execution internally, returning only final answer to client
"""
import os
import requests
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from services.customer_memory import CustomerMemoryService
from services.context_manager import ContextManager, ContextType
import time
import models

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

# Available tools for menu queries
AVAILABLE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_dish_details",
            "description": "Get complete details about a specific dish including ingredients, allergens, and price",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish_name": {
                        "type": "string",
                        "description": "The name of the dish to look up"
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
                        "enum": ["ingredient", "category", "name"],
                        "description": "Type of search to perform"
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
            "description": "Find dishes that meet specific dietary restrictions",
            "parameters": {
                "type": "object",
                "properties": {
                    "restrictions": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["vegetarian", "vegan", "gluten-free", "nut-free", "dairy-free"]
                        },
                        "description": "List of dietary restrictions to filter by"
                    }
                },
                "required": ["restrictions"]
            }
        }
    }
]

def execute_tool(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool locally and return results"""
    try:
        if tool_name == "get_dish_details":
            dish_name = parameters.get("dish_name", "").lower()
            
            # Find the dish
            for item in menu_items:
                if item.get('dish', '').lower() == dish_name or item.get('name', '').lower() == dish_name:
                    return {
                        "success": True,
                        "dish": {
                            "name": item.get('dish') or item.get('name'),
                            "price": item.get('price'),
                            "description": item.get('description'),
                            "ingredients": item.get('ingredients', []),
                            "allergens": item.get('allergens', []),
                            "dietary_info": {
                                "vegetarian": item.get('is_vegetarian', False),
                                "vegan": item.get('is_vegan', False),
                                "gluten_free": item.get('is_gluten_free', False)
                            }
                        }
                    }
            
            return {
                "success": False,
                "error": f"Dish '{parameters.get('dish_name')}' not found"
            }
        
        elif tool_name == "search_menu_items":
            search_term = parameters.get("search_term", "").lower()
            search_type = parameters.get("search_type", "name")
            results = []
            
            for item in menu_items:
                match = False
                
                if search_type == "name":
                    if search_term in (item.get('dish', '') or item.get('name', '')).lower():
                        match = True
                elif search_type == "category":
                    if search_term in item.get('category', '').lower():
                        match = True
                elif search_type == "ingredient":
                    ingredients = item.get('ingredients', [])
                    if any(search_term in ing.lower() for ing in ingredients):
                        match = True
                
                if match:
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "brief": f"{item.get('dish', '')} - {item.get('price', '')}"
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results[:10]  # Limit to 10 items
            }
        
        elif tool_name == "filter_by_dietary":
            restrictions = parameters.get("restrictions", [])
            results = []
            
            for item in menu_items:
                suitable = True
                
                for restriction in restrictions:
                    if restriction == "vegetarian" and not item.get('is_vegetarian', False):
                        suitable = False
                    elif restriction == "vegan" and not item.get('is_vegan', False):
                        suitable = False
                    elif restriction == "gluten-free" and not item.get('is_gluten_free', False):
                        suitable = False
                    elif restriction == "nut-free" and not item.get('is_nut_free', True):
                        suitable = False
                    elif restriction == "dairy-free" and not item.get('is_dairy_free', False):
                        suitable = False
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "allergens": item.get('allergens', [])
                    })
            
            return {
                "success": True,
                "count": len(results),
                "items": results,
                "restrictions_applied": restrictions
            }
        
        else:
            return {
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def call_mia_api(message: str, tools: Optional[List[Dict]] = None, context: Optional[Dict] = None, max_tokens: int = 300) -> Dict:
    """Make a single call to MIA API"""
    try:
        request_data = {
            "message": message,
            "context": context or {},
            "max_tokens": max_tokens,
            "temperature": 0.7
        }
        
        if tools:
            request_data["tools"] = tools
            request_data["tool_choice"] = "auto"
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"MIA API error: {response.status_code}")
            return None
    
    except Exception as e:
        logger.error(f"MIA API call failed: {e}")
        return None

def build_tool_discovery_prompt(customer_message: str, restaurant_name: str) -> str:
    """Build minimal prompt for tool discovery"""
    return f"""You are an AI assistant for {restaurant_name} restaurant.

Customer asks: {customer_message}

If the customer is asking about specific dishes, ingredients, allergens, or dietary options, use the appropriate tool.
For general greetings or non-menu questions, respond naturally without tools."""

def build_final_response_prompt(customer_message: str, tool_results: List[Dict], restaurant_name: str, customer_name: Optional[str] = None) -> str:
    """Build full prompt with tool results for final response"""
    prompt = f"""You are Maria, a friendly and knowledgeable server at {restaurant_name}.

Customer{f' ({customer_name})' if customer_name else ''} asked: {customer_message}

Based on our menu database, here's the accurate information:

"""
    
    for i, result in enumerate(tool_results):
        if result.get("success"):
            prompt += f"Tool Result {i+1}:\n{json.dumps(result, indent=2)}\n\n"
    
    prompt += """Using the above information, provide a natural, friendly, and helpful response. Include:
- Accurate details from the tool results
- Natural conversation flow
- Any helpful suggestions or additional context
- Maintain warm, professional tone

Do not mention "tool" or "database" - speak naturally as a server would."""
    
    return prompt

def generate_response_internal_tools(req: Any, db: Session) -> Dict:
    """Generate response using internal tool flow"""
    try:
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter_by(
            restaurant_id=req.restaurant_id
        ).first()
        
        if not restaurant:
            return {"answer": "Restaurant not found"}
        
        restaurant_data = restaurant.data if isinstance(restaurant.data, dict) else json.loads(restaurant.data)
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        menu_items = restaurant_data.get('menu', [])
        
        # Get customer profile
        customer_profile = CustomerMemoryService.get_or_create_profile(
            db, req.client_id, req.restaurant_id
        )
        customer_name = customer_profile.name if customer_profile else None
        
        # Phase 1: Tool Discovery (minimal context)
        discovery_prompt = build_tool_discovery_prompt(req.message, restaurant_name)
        
        logger.info("Phase 1: Tool discovery")
        discovery_response = call_mia_api(
            message=discovery_prompt,
            tools=AVAILABLE_TOOLS,
            context={"restaurant_name": restaurant_name},
            max_tokens=150  # Keep discovery response short
        )
        
        if not discovery_response:
            return {"answer": "I'm having trouble processing your request. Please try again."}
        
        # Check if we got a direct response or need to handle tools
        if discovery_response.get("status") == "completed":
            tool_calls = discovery_response.get("tool_calls", [])
            
            if tool_calls:
                # Phase 2: Execute tools and get final response
                logger.info(f"Phase 2: Executing {len(tool_calls)} tools")
                tool_results = []
                
                for tool_call in tool_calls:
                    if isinstance(tool_call, dict) and "function" in tool_call:
                        tool_name = tool_call["function"].get("name")
                        args_str = tool_call["function"].get("arguments", "{}")
                        
                        try:
                            parameters = json.loads(args_str) if isinstance(args_str, str) else args_str
                        except:
                            parameters = {}
                        
                        logger.info(f"Executing tool: {tool_name} with params: {parameters}")
                        result = execute_tool(tool_name, parameters, menu_items)
                        tool_results.append(result)
                
                # Build final response with tool results
                final_prompt = build_final_response_prompt(
                    req.message, 
                    tool_results, 
                    restaurant_name,
                    customer_name
                )
                
                logger.info("Phase 3: Generating final response with tool results")
                final_response = call_mia_api(
                    message=final_prompt,
                    tools=None,  # No tools in final call
                    context={
                        "restaurant_name": restaurant_name,
                        "role": "friendly server"
                    }
                )
                
                if final_response and final_response.get("status") == "completed":
                    response_text = final_response.get("response", "")
                    
                    # Extract any learned information
                    extracted_info = CustomerMemoryService.extract_customer_info(response_text, customer_profile)
                    if extracted_info:
                        CustomerMemoryService.update_customer_profile(db, req.client_id, req.restaurant_id, extracted_info)
                    
                    return {
                        "answer": response_text,
                        "used_tools": True,
                        "tool_count": len(tool_calls)
                    }
            
            else:
                # No tools needed, use discovery response
                response_text = discovery_response.get("response", "")
                
                # But let's enhance it with full context
                enhance_prompt = f"""You are Maria, a friendly server at {restaurant_name}.

The customer{f' ({customer_name})' if customer_name else ''} said: {req.message}

Provide a warm, helpful response. You work at an Italian restaurant with a variety of dishes."""
                
                enhanced_response = call_mia_api(
                    message=enhance_prompt,
                    context={"restaurant_name": restaurant_name}
                )
                
                if enhanced_response and enhanced_response.get("status") == "completed":
                    response_text = enhanced_response.get("response", response_text)
                
                return {
                    "answer": response_text,
                    "used_tools": False,
                    "tool_count": 0
                }
        
        # Fallback
        return {"answer": "I'm here to help! What would you like to know about our menu?"}
        
    except Exception as e:
        logger.error(f"Error in internal tools service: {e}", exc_info=True)
        return {"answer": "I apologize, but I'm having trouble accessing the menu information. Please try again."}

# Make it compatible with the existing interface
def mia_chat_service_internal_tools(req: Any, db: Session) -> Any:
    """Wrapper for compatibility with chat_dynamic.py"""
    from schemas.chat import ChatResponse
    
    result = generate_response_internal_tools(req, db)
    
    return ChatResponse(
        answer=result.get("answer", ""),
        response_id=None,
        confidence_score=0.95 if result.get("used_tools") else 0.85
    )