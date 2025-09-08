"""
MIA Chat Service with Internal Tool Flow V2
First call: AI returns tools to use (not customer response)
Second call: AI generates customer response with tool results
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
            
            # Find the dish (fuzzy matching)
            for item in menu_items:
                item_name = (item.get('dish') or item.get('name', '')).lower().strip()
                if dish_name in item_name or item_name in dish_name:
                    return {
                        "tool": "get_dish_details",
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
                "tool": "get_dish_details",
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
                    if search_term in item.get('category', '').lower() or search_term in item.get('subcategory', '').lower():
                        match = True
                elif search_type == "ingredient":
                    ingredients = item.get('ingredients', [])
                    if any(search_term in ing.lower() for ing in ingredients):
                        match = True
                
                if match:
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "category": item.get('category', ''),
                        "allergens": item.get('allergens', [])
                    })
            
            return {
                "tool": "search_menu_items",
                "success": True,
                "search_term": search_term,
                "search_type": search_type,
                "count": len(results),
                "items": results[:15]  # Limit results
            }
        
        elif tool_name == "filter_by_dietary":
            restrictions = parameters.get("restrictions", [])
            results = []
            
            for item in menu_items:
                suitable = True
                allergens = [a.lower() for a in item.get('allergens', [])]
                ingredients = ' '.join(item.get('ingredients', [])).lower()
                
                for restriction in restrictions:
                    restriction_lower = restriction.lower()
                    
                    if restriction_lower == "nut-free":
                        if any("nut" in a for a in allergens) or "nut" in ingredients:
                            suitable = False
                    elif restriction_lower == "dairy-free":
                        if "dairy" in allergens or "lactose" in allergens or any(d in ingredients for d in ["milk", "cheese", "cream", "butter"]):
                            suitable = False
                    elif restriction_lower == "gluten-free":
                        if "gluten" in allergens or "wheat" in allergens:
                            suitable = False
                    elif restriction_lower == "vegetarian":
                        meat_words = ['meat', 'chicken', 'beef', 'pork', 'lamb', 'fish', 'seafood', 'shrimp']
                        if any(word in ingredients for word in meat_words):
                            suitable = False
                    elif restriction_lower == "vegan":
                        non_vegan = ['meat', 'chicken', 'beef', 'fish', 'egg', 'dairy', 'cheese', 'milk', 'cream', 'butter', 'honey']
                        if any(word in ingredients for word in non_vegan):
                            suitable = False
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name'),
                        "price": item.get('price'),
                        "category": item.get('category', ''),
                        "allergens": item.get('allergens', [])
                    })
            
            return {
                "tool": "filter_by_dietary",
                "success": True,
                "restrictions": restrictions,
                "count": len(results),
                "items": results
            }
        
        else:
            return {
                "tool": tool_name,
                "success": False,
                "error": f"Unknown tool: {tool_name}"
            }
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {
            "tool": tool_name,
            "success": False,
            "error": str(e)
        }

def build_tool_analysis_prompt(customer_message: str) -> str:
    """Build prompt for AI to analyze message and return tools to use"""
    return f"""Analyze this customer message and determine which tools to use:

Customer message: "{customer_message}"

ANALYSIS RULES:
1. Identify ALL intents in the message (there may be multiple)
2. Return ONLY the tool calls needed, no text response
3. For allergies/dietary restrictions, use filter_by_dietary
4. For specific dish questions, use get_dish_details
5. For category/type searches, use search_menu_items

Examples:
- "I love pasta and I'm allergic to nuts" → search_menu_items(pasta, category) + filter_by_dietary([nut-free])
- "Tell me about the carbonara" → get_dish_details(carbonara)
- "What vegetarian options do you have?" → filter_by_dietary([vegetarian])
- "Do you have seafood?" → search_menu_items(seafood, category)

Analyze the message and return the appropriate tool calls. If no tools are needed (just greeting), you can respond without tools."""

def build_customer_response_prompt(customer_message: str, tool_results: List[Dict], restaurant_name: str, customer_profile: Optional[Any] = None) -> str:
    """Build prompt for final customer response using tool results"""
    prompt = f"""You are Maria, a warm and knowledgeable server at {restaurant_name}.

CUSTOMER MESSAGE: "{customer_message}"

"""
    
    if customer_profile and (customer_profile.allergies or customer_profile.dietary_restrictions):
        prompt += f"""CUSTOMER PROFILE:
- Name: {customer_profile.name or 'Guest'}
- Allergies: {', '.join(customer_profile.allergies) if customer_profile.allergies else 'None'}
- Dietary Restrictions: {', '.join(customer_profile.dietary_restrictions) if customer_profile.dietary_restrictions else 'None'}

"""
    
    prompt += "INFORMATION FROM OUR MENU:\n"
    
    for result in tool_results:
        prompt += f"\n{json.dumps(result, indent=2)}\n"
    
    prompt += """
RESPONSE GUIDELINES:
1. Use ONLY the information provided above
2. Be natural and conversational - you're Maria, not a robot
3. If customer has allergies, always mention safety precautions
4. Include specific details (names, prices, ingredients)
5. If no results found, suggest alternatives
6. Never mention "tools" or "database" - speak naturally

Respond as Maria would:"""
    
    return prompt

def generate_response_internal_tools_v2(req: Any, db: Session) -> Any:
    """Generate response using proper two-phase internal tool flow"""
    from schemas.chat import ChatResponse
    
    try:
        logger.info(f"=== Internal Tools V2 Start - Restaurant: {req.restaurant_id} ===")
        
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter_by(
            restaurant_id=req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(
                answer="I apologize, but I couldn't find the restaurant information.",
                response_id=None,
                confidence_score=0.0
            )
        
        # Parse restaurant data
        try:
            restaurant_data = restaurant.data if isinstance(restaurant.data, dict) else json.loads(restaurant.data)
        except:
            restaurant_data = {}
        
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        menu_items = restaurant_data.get('menu', [])
        
        logger.info(f"Restaurant: {restaurant_name}, Menu items: {len(menu_items)}")
        
        # Get customer profile
        customer_profile = None
        try:
            from services.customer_memory import CustomerMemoryService
            customer_profile = CustomerMemoryService.get_or_create_profile(
                db, req.client_id, req.restaurant_id
            )
        except Exception as e:
            logger.warning(f"Could not get customer profile: {e}")
        
        # === PHASE 1: Tool Analysis ===
        logger.info("PHASE 1: Analyzing message for tool usage")
        analysis_prompt = build_tool_analysis_prompt(req.message)
        
        analysis_response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": analysis_prompt,
                "tools": AVAILABLE_TOOLS,
                "tool_choice": "auto",
                "max_tokens": 200,
                "temperature": 0.3  # Lower temperature for more consistent tool selection
            },
            timeout=10
        )
        
        if analysis_response.status_code != 200:
            logger.error(f"Analysis phase failed: {analysis_response.status_code}")
            return ChatResponse(
                answer="I'm having trouble understanding your request. Could you please try again?",
                response_id=None,
                confidence_score=0.0
            )
        
        analysis_data = analysis_response.json()
        
        # Handle different response types
        if analysis_data.get("status") == "completed":
            tool_calls = analysis_data.get("tool_calls", [])
            
            if not tool_calls:
                # No tools needed - simple response
                logger.info("No tools needed, generating direct response")
                simple_prompt = f"""You are Maria at {restaurant_name}.
Customer said: "{req.message}"
Respond warmly and helpfully."""
                
                response = requests.post(
                    f"{MIA_BACKEND_URL}/chat",
                    json={"message": simple_prompt, "max_tokens": 200},
                    timeout=10
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return ChatResponse(
                        answer=data.get("response", "Hello! How can I help you today?"),
                        response_id=data.get("job_id"),
                        confidence_score=0.85
                    )
            
            # === PHASE 2: Execute Tools ===
            logger.info(f"PHASE 2: Executing {len(tool_calls)} tools")
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
                    logger.info(f"Tool {tool_name} returned {result.get('count', 0) if 'count' in result else 'data'}")
            
            # === PHASE 3: Generate Customer Response ===
            logger.info("PHASE 3: Generating customer response with tool results")
            response_prompt = build_customer_response_prompt(
                req.message,
                tool_results,
                restaurant_name,
                customer_profile
            )
            
            final_response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={
                    "message": response_prompt,
                    "max_tokens": 400,
                    "temperature": 0.7
                },
                timeout=10
            )
            
            if final_response.status_code == 200:
                final_data = final_response.json()
                response_text = final_data.get("response", "")
                
                # Update customer profile if new info detected
                if customer_profile:
                    try:
                        extracted = CustomerMemoryService.extract_customer_info(req.message, customer_profile)
                        if extracted:
                            CustomerMemoryService.update_customer_profile(db, req.client_id, req.restaurant_id, extracted)
                    except:
                        pass
                
                return ChatResponse(
                    answer=response_text,
                    response_id=final_data.get("job_id"),
                    confidence_score=0.95
                )
        
        # Fallback
        return ChatResponse(
            answer="I'd be happy to help you with our menu. What would you like to know?",
            response_id=None,
            confidence_score=0.5
        )
        
    except Exception as e:
        logger.error(f"Error in internal tools V2: {e}", exc_info=True)
        return ChatResponse(
            answer="I apologize for the inconvenience. Please try again.",
            response_id=None,
            confidence_score=0.0
        )

# Wrapper for compatibility
def mia_chat_service_internal_tools_v2(req: Any, db: Session) -> Any:
    """Wrapper for compatibility with chat_dynamic.py"""
    return generate_response_internal_tools_v2(req, db)