"""
MIA Chat Service with Internal Tool Flow V3
First call: AI MUST select from predefined tool names only
Second call: Backend sends actual tool schemas for selected tools
Third call: Generate customer response
"""
import os
import requests
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

# Tool Registry - Maps tool names to their actual implementations
TOOL_REGISTRY = {
    # Menu Tools
    "get_dish_details": {
        "description": "Get complete information about a specific dish",
        "when_to_use": "Customer asks about specific dish details, ingredients, or allergens",
        "schema": {
            "type": "function",
            "function": {
                "name": "get_dish_details",
                "description": "Get complete details about a specific dish",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "dish_name": {"type": "string", "description": "Name of the dish"}
                    },
                    "required": ["dish_name"]
                }
            }
        }
    },
    "search_menu_by_category": {
        "description": "Search menu items by category (pasta, seafood, appetizers, etc)",
        "when_to_use": "Customer asks what types of dishes you have",
        "schema": {
            "type": "function",
            "function": {
                "name": "search_menu_items",
                "description": "Search menu by category",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_term": {"type": "string"},
                        "search_type": {"type": "string", "enum": ["category"], "default": "category"}
                    },
                    "required": ["search_term"]
                }
            }
        }
    },
    "search_menu_by_ingredient": {
        "description": "Search menu items containing specific ingredients",
        "when_to_use": "Customer asks for dishes with specific ingredients",
        "schema": {
            "type": "function",
            "function": {
                "name": "search_menu_items",
                "description": "Search menu by ingredient",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "search_term": {"type": "string"},
                        "search_type": {"type": "string", "enum": ["ingredient"], "default": "ingredient"}
                    },
                    "required": ["search_term"]
                }
            }
        }
    },
    "filter_vegetarian": {
        "description": "Show only vegetarian dishes",
        "when_to_use": "Customer is vegetarian",
        "schema": {
            "type": "function",
            "function": {
                "name": "filter_by_dietary",
                "description": "Filter vegetarian dishes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "restrictions": {"type": "array", "items": {"type": "string"}, "default": ["vegetarian"]}
                    }
                }
            }
        }
    },
    "filter_vegan": {
        "description": "Show only vegan dishes",
        "when_to_use": "Customer is vegan",
        "schema": {
            "type": "function",
            "function": {
                "name": "filter_by_dietary",
                "description": "Filter vegan dishes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "restrictions": {"type": "array", "items": {"type": "string"}, "default": ["vegan"]}
                    }
                }
            }
        }
    },
    "filter_gluten_free": {
        "description": "Show only gluten-free dishes",
        "when_to_use": "Customer needs gluten-free options",
        "schema": {
            "type": "function",
            "function": {
                "name": "filter_by_dietary",
                "description": "Filter gluten-free dishes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "restrictions": {"type": "array", "items": {"type": "string"}, "default": ["gluten-free"]}
                    }
                }
            }
        }
    },
    "filter_nut_free": {
        "description": "Show only nut-free dishes",
        "when_to_use": "Customer has nut allergy",
        "schema": {
            "type": "function",
            "function": {
                "name": "filter_by_dietary",
                "description": "Filter nut-free dishes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "restrictions": {"type": "array", "items": {"type": "string"}, "default": ["nut-free"]}
                    }
                }
            }
        }
    },
    "filter_dairy_free": {
        "description": "Show only dairy-free dishes",
        "when_to_use": "Customer is lactose intolerant or dairy-free",
        "schema": {
            "type": "function",
            "function": {
                "name": "filter_by_dietary",
                "description": "Filter dairy-free dishes",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "restrictions": {"type": "array", "items": {"type": "string"}, "default": ["dairy-free"]}
                    }
                }
            }
        }
    },
    "no_tool_needed": {
        "description": "No tool needed - simple greeting or general question",
        "when_to_use": "Customer says hello, goodbye, or asks non-menu questions",
        "schema": None
    }
}

def get_tool_list_prompt(customer_message: str) -> str:
    """Build prompt for tool selection - AI must pick from list"""
    tool_list = []
    for tool_name, tool_info in TOOL_REGISTRY.items():
        tool_list.append(f"- {tool_name}: {tool_info['description']} (Use when: {tool_info['when_to_use']})")
    
    return f"""Analyze this message and select ALL applicable tools from the list below.

Customer message: "{customer_message}"

AVAILABLE TOOLS:
{chr(10).join(tool_list)}

RULES:
1. You MUST respond with ONLY tool names from the list above
2. If multiple tools apply, list all of them
3. Return as JSON array: ["tool_name1", "tool_name2"]
4. For allergies AND menu search, use both relevant tools
5. If no tools needed, return: ["no_tool_needed"]

Examples:
- "I'm vegan and want pasta" → ["filter_vegan", "search_menu_by_category"]
- "Tell me about the carbonara" → ["get_dish_details"]
- "I have a nut allergy" → ["filter_nut_free"]
- "Hello there" → ["no_tool_needed"]
- "What gluten-free pasta do you have?" → ["filter_gluten_free", "search_menu_by_category"]

Respond with ONLY the JSON array of tool names."""

def execute_tool_from_registry(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a tool based on registry mapping"""
    if tool_name not in TOOL_REGISTRY:
        return {"error": f"Unknown tool: {tool_name}"}
    
    tool_info = TOOL_REGISTRY[tool_name]
    if not tool_info["schema"]:
        return {"info": "No execution needed"}
    
    actual_function = tool_info["schema"]["function"]["name"]
    
    # Execute based on actual function name
    if actual_function == "get_dish_details":
        dish_name = parameters.get("dish_name", "").lower()
        for item in menu_items:
            if dish_name in (item.get('dish', '') or item.get('name', '')).lower():
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
        return {"tool": tool_name, "found": False, "error": "Dish not found"}
    
    elif actual_function == "search_menu_items":
        search_term = parameters.get("search_term", "").lower()
        search_type = parameters.get("search_type", "category")
        results = []
        
        for item in menu_items:
            match = False
            if search_type == "category":
                if search_term in item.get('category', '').lower() or search_term in item.get('subcategory', '').lower():
                    match = True
            elif search_type == "ingredient":
                if any(search_term in ing.lower() for ing in item.get('ingredients', [])):
                    match = True
            
            if match:
                results.append({
                    "name": item.get('dish') or item.get('name'),
                    "price": item.get('price'),
                    "category": item.get('category'),
                    "description": item.get('description', '')[:100]
                })
        
        return {
            "tool": tool_name,
            "search_term": search_term,
            "found": len(results),
            "items": results[:10]
        }
    
    elif actual_function == "filter_by_dietary":
        restrictions = parameters.get("restrictions", [])
        results = []
        
        for item in menu_items:
            suitable = True
            allergens = [a.lower() for a in item.get('allergens', [])]
            ingredients_text = ' '.join(item.get('ingredients', [])).lower()
            
            for restriction in restrictions:
                if restriction == "nut-free" and any("nut" in a for a in allergens):
                    suitable = False
                elif restriction == "dairy-free" and "dairy" in allergens:
                    suitable = False
                elif restriction == "gluten-free" and "gluten" in allergens:
                    suitable = False
                elif restriction == "vegetarian":
                    meats = ['meat', 'chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood']
                    if any(m in ingredients_text for m in meats):
                        suitable = False
                elif restriction == "vegan":
                    animal = ['meat', 'chicken', 'beef', 'fish', 'egg', 'dairy', 'milk', 'cheese', 'butter']
                    if any(a in ingredients_text for a in animal):
                        suitable = False
            
            if suitable:
                results.append({
                    "name": item.get('dish') or item.get('name'),
                    "price": item.get('price'),
                    "category": item.get('category'),
                    "allergens": item.get('allergens', [])
                })
        
        return {
            "tool": tool_name,
            "restriction": restrictions[0] if restrictions else "unknown",
            "found": len(results),
            "items": results
        }
    
    return {"error": "Tool execution not implemented"}

def generate_response_internal_tools_v3(req: Any, db: Session) -> Any:
    """Three-phase flow with constrained tool selection"""
    from schemas.chat import ChatResponse
    
    try:
        logger.info(f"=== Internal Tools V3 - Restaurant: {req.restaurant_id} ===")
        
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter_by(
            restaurant_id=req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="Restaurant not found", response_id=None, confidence_score=0.0)
        
        try:
            restaurant_data = restaurant.data if isinstance(restaurant.data, dict) else json.loads(restaurant.data)
        except:
            restaurant_data = {}
        
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        menu_items = restaurant_data.get('menu', [])
        
        # === PHASE 1: Tool Selection (Constrained) ===
        logger.info("PHASE 1: Tool selection from predefined list")
        tool_selection_prompt = get_tool_list_prompt(req.message)
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": tool_selection_prompt,
                "max_tokens": 100,
                "temperature": 0.1  # Very low for consistent selection
            },
            timeout=10
        )
        
        if response.status_code != 200:
            return ChatResponse(answer="I'm having trouble understanding your request.", response_id=None, confidence_score=0.0)
        
        # Parse tool selection
        selection_text = response.json().get("response", "").strip()
        try:
            # Try to extract JSON array from response
            if "[" in selection_text and "]" in selection_text:
                start = selection_text.find("[")
                end = selection_text.rfind("]") + 1
                selected_tools = json.loads(selection_text[start:end])
            else:
                selected_tools = ["no_tool_needed"]
        except:
            selected_tools = ["no_tool_needed"]
        
        logger.info(f"Selected tools: {selected_tools}")
        
        # If no tools needed, generate simple response
        if selected_tools == ["no_tool_needed"]:
            simple_prompt = f"""You are Maria at {restaurant_name}.
Customer said: "{req.message}"
Respond warmly and professionally."""
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={"message": simple_prompt, "max_tokens": 200},
                timeout=10
            )
            
            if response.status_code == 200:
                return ChatResponse(
                    answer=response.json().get("response", "Hello! How can I help you today?"),
                    response_id=response.json().get("job_id"),
                    confidence_score=0.85
                )
        
        # === PHASE 2: Execute Selected Tools ===
        logger.info(f"PHASE 2: Executing {len(selected_tools)} tools")
        
        # Build tool schemas for selected tools only
        tool_schemas = []
        for tool_name in selected_tools:
            if tool_name in TOOL_REGISTRY and TOOL_REGISTRY[tool_name]["schema"]:
                tool_schemas.append(TOOL_REGISTRY[tool_name]["schema"])
        
        if not tool_schemas:
            return ChatResponse(answer="I couldn't find the information you're looking for.", response_id=None, confidence_score=0.0)
        
        # Call MIA with specific tools to get parameters
        param_prompt = f"""Customer asked: "{req.message}"

You have these tools available. Call the appropriate ones with correct parameters:"""
        
        param_response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": param_prompt,
                "tools": tool_schemas,
                "tool_choice": "auto",
                "max_tokens": 200
            },
            timeout=10
        )
        
        if param_response.status_code != 200:
            return ChatResponse(answer="I'm having trouble processing your request.", response_id=None, confidence_score=0.0)
        
        # Execute tools locally
        tool_results = []
        param_data = param_response.json()
        
        if param_data.get("tool_calls"):
            for tool_call in param_data["tool_calls"]:
                if "function" in tool_call:
                    func_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"].get("arguments", "{}"))
                    
                    # Find which registry tool this maps to
                    for reg_name, reg_info in TOOL_REGISTRY.items():
                        if reg_info["schema"] and reg_info["schema"]["function"]["name"] == func_name:
                            result = execute_tool_from_registry(reg_name, args, menu_items)
                            tool_results.append(result)
                            break
        
        # === PHASE 3: Generate Customer Response ===
        logger.info("PHASE 3: Generating final response")
        
        response_prompt = f"""You are Maria, a warm server at {restaurant_name}.

Customer asked: "{req.message}"

Information from our menu:
{json.dumps(tool_results, indent=2)}

Generate a natural, helpful response using ONLY the information above. Be specific about dishes, prices, and any dietary information."""
        
        final_response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={"message": response_prompt, "max_tokens": 400},
            timeout=10
        )
        
        if final_response.status_code == 200:
            return ChatResponse(
                answer=final_response.json().get("response", ""),
                response_id=final_response.json().get("job_id"),
                confidence_score=0.95
            )
        
        return ChatResponse(
            answer="I apologize for the inconvenience. Please try again.",
            response_id=None,
            confidence_score=0.0
        )
        
    except Exception as e:
        logger.error(f"Error in V3: {e}", exc_info=True)
        return ChatResponse(
            answer="I apologize for the technical difficulty. Please try again.",
            response_id=None,
            confidence_score=0.0
        )

# Wrapper
def mia_chat_service_internal_tools_v3(req: Any, db: Session) -> Any:
    return generate_response_internal_tools_v3(req, db)