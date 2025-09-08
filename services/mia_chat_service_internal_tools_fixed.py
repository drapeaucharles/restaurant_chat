"""
MIA Chat Service with Internal Tool Flow - Fixed Version
Handles tool discovery and execution internally with strict formatting
"""
import os
import requests
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
from services.customer_memory import CustomerMemoryService
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
        logger.info(f"Executing tool: {tool_name} with params: {parameters}")
        
        if tool_name == "get_dish_details":
            dish_name = parameters.get("dish_name", "").lower().strip()
            
            # Find the dish
            for item in menu_items:
                item_name = (item.get('dish') or item.get('name', '')).lower().strip()
                if dish_name in item_name or item_name in dish_name:
                    return {
                        "success": True,
                        "dish": {
                            "name": item.get('dish') or item.get('name'),
                            "price": item.get('price'),
                            "description": item.get('description'),
                            "ingredients": item.get('ingredients', []),
                            "allergens": item.get('allergens', [])
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
                "items": results[:10]
            }
        
        elif tool_name == "filter_by_dietary":
            restrictions = parameters.get("restrictions", [])
            results = []
            
            for item in menu_items:
                suitable = True
                allergens = [a.lower() for a in item.get('allergens', [])]
                
                for restriction in restrictions:
                    restriction_lower = restriction.lower()
                    
                    if restriction_lower == "nut-free" and any("nut" in a for a in allergens):
                        suitable = False
                    elif restriction_lower == "dairy-free" and "dairy" in allergens:
                        suitable = False
                    elif restriction_lower == "gluten-free" and "gluten" in allergens:
                        suitable = False
                    # Add more restriction checks as needed
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "allergens": item.get('allergens', [])
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
        logger.error(f"Tool execution error: {e}")
        return {
            "success": False,
            "error": str(e)
        }

def call_mia_api(message: str, tools: Optional[List[Dict]] = None, context: Optional[Dict] = None, max_tokens: int = 300) -> Dict:
    """Make a single call to MIA API with proper error handling"""
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
        
        logger.info(f"Calling MIA API with message length: {len(message)}, tools: {len(tools) if tools else 0}")
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"MIA API response status: {result.get('status')}")
            return result
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            return None
    
    except Exception as e:
        logger.error(f"MIA API call failed: {e}")
        return None

def build_tool_discovery_prompt(customer_message: str, restaurant_name: str) -> str:
    """Build minimal prompt for tool discovery with strict formatting"""
    return f"""You are an AI assistant for {restaurant_name} restaurant.

Customer asks: {customer_message}

STRICT RULES:
1. If the customer asks about specific dishes, ingredients, allergens, or dietary options, you MUST use the appropriate tool
2. For simple greetings or non-menu questions, respond directly without tools
3. Keep your response brief - just acknowledge and use the tool if needed

RESPONSE FORMAT:
- If using a tool: Just say "Let me check that for you" and call the tool
- If no tool needed: Provide a direct, brief response

DO NOT provide menu information without using tools first."""

def build_final_response_prompt(customer_message: str, tool_results: List[Dict], restaurant_name: str) -> str:
    """Build full prompt with tool results for final response"""
    prompt = f"""You are Maria, a friendly and knowledgeable server at {restaurant_name}.

Customer asked: {customer_message}

TOOL RESULTS FROM DATABASE:
"""
    
    for i, result in enumerate(tool_results):
        if result.get("success"):
            prompt += f"\n{json.dumps(result, indent=2)}\n"
        else:
            prompt += f"\nTool {i+1} failed: {result.get('error', 'Unknown error')}\n"
    
    prompt += """
STRICT RESPONSE RULES:
1. Use ONLY the information from the tool results above
2. Be natural and conversational - don't mention "tools" or "database"
3. Include specific details like prices and ingredients
4. If a tool failed or found no results, be honest about it
5. Maintain a warm, professional tone as a server would

Provide your response as Maria:"""
    
    return prompt

def generate_response_internal_tools(req: Any, db: Session) -> Any:
    """Generate response using internal tool flow - Fixed version"""
    from schemas.chat import ChatResponse
    
    try:
        logger.info(f"Internal tools service called for restaurant: {req.restaurant_id}")
        
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter_by(
            restaurant_id=req.restaurant_id
        ).first()
        
        if not restaurant:
            logger.error(f"Restaurant not found: {req.restaurant_id}")
            return ChatResponse(
                answer="I apologize, but I couldn't find the restaurant information.",
                response_id=None,
                confidence_score=0.0
            )
        
        # Parse restaurant data
        try:
            restaurant_data = restaurant.data if isinstance(restaurant.data, dict) else json.loads(restaurant.data)
        except Exception as e:
            logger.error(f"Failed to parse restaurant data: {e}")
            restaurant_data = {}
        
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        menu_items = restaurant_data.get('menu', [])
        
        logger.info(f"Restaurant: {restaurant_name}, Menu items: {len(menu_items)}")
        
        # Phase 1: Tool Discovery
        discovery_prompt = build_tool_discovery_prompt(req.message, restaurant_name)
        
        logger.info("Phase 1: Calling MIA for tool discovery")
        discovery_response = call_mia_api(
            message=discovery_prompt,
            tools=AVAILABLE_TOOLS,
            context={"restaurant_name": restaurant_name},
            max_tokens=150
        )
        
        if not discovery_response:
            logger.error("Discovery response is None")
            return ChatResponse(
                answer="I'm having trouble processing your request. Please try again.",
                response_id=None,
                confidence_score=0.0
            )
        
        # Check for immediate response (completed status)
        if discovery_response.get("status") == "completed":
            tool_calls = discovery_response.get("tool_calls", [])
            
            if tool_calls:
                # Phase 2: Execute tools and generate final response
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
                        
                        result = execute_tool(tool_name, parameters, menu_items)
                        tool_results.append(result)
                
                # Generate final response with tool results
                final_prompt = build_final_response_prompt(req.message, tool_results, restaurant_name)
                
                logger.info("Phase 3: Generating final response with tool results")
                final_response = call_mia_api(
                    message=final_prompt,
                    tools=None,
                    context={"restaurant_name": restaurant_name}
                )
                
                if final_response and final_response.get("status") == "completed":
                    response_text = final_response.get("response", "")
                    return ChatResponse(
                        answer=response_text,
                        response_id=final_response.get("job_id"),
                        confidence_score=0.95
                    )
            
            else:
                # No tools needed, use discovery response
                response_text = discovery_response.get("response", "")
                return ChatResponse(
                    answer=response_text,
                    response_id=discovery_response.get("job_id"),
                    confidence_score=0.85
                )
        
        # Handle queued response (shouldn't happen with push architecture)
        elif discovery_response.get("status") == "queued":
            logger.warning("Got queued response - push architecture might not be working")
            return ChatResponse(
                answer="I'm processing your request. Please try again in a moment.",
                response_id=None,
                confidence_score=0.0
            )
        
        # Unknown status
        logger.error(f"Unknown response status: {discovery_response.get('status')}")
        return ChatResponse(
            answer="I apologize, but I'm having trouble understanding your request.",
            response_id=None,
            confidence_score=0.0
        )
        
    except Exception as e:
        logger.error(f"Error in internal tools service: {e}", exc_info=True)
        return ChatResponse(
            answer="I apologize, but I'm having technical difficulties. Please try again.",
            response_id=None,
            confidence_score=0.0
        )

# Make it compatible with the existing interface
def mia_chat_service_internal_tools_fixed(req: Any, db: Session) -> Any:
    """Wrapper for compatibility with chat_dynamic.py"""
    return generate_response_internal_tools(req, db)