"""
MIA Chat Service - Full Menu Compact with Tool Support
Sends compact menu catalog with tool definitions for detail queries
"""
import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse
from services.customer_memory_service import CustomerMemoryService
from services.mia_direct_api_v2 import MiaDirectAPI

logger = logging.getLogger(__name__)

# Tool definitions for MIA
MENU_QUERY_TOOLS = [
    {
        "name": "get_dish_details",
        "description": "Get complete details about a specific menu item including description, ingredients, allergens, and price",
        "parameters": {
            "dish_name": {
                "type": "string",
                "description": "The exact name of the dish to get details for"
            }
        }
    },
    {
        "name": "search_by_ingredient",
        "description": "Find all dishes that contain a specific ingredient",
        "parameters": {
            "ingredient": {
                "type": "string",
                "description": "The ingredient to search for (e.g., 'tomato', 'chicken', 'pasta')"
            }
        }
    },
    {
        "name": "filter_by_category",
        "description": "Get all dishes in a specific category",
        "parameters": {
            "category": {
                "type": "string",
                "description": "The category to filter by (e.g., 'appetizer', 'main course', 'dessert')"
            }
        }
    },
    {
        "name": "check_dietary_restriction",
        "description": "Find dishes suitable for specific dietary restrictions",
        "parameters": {
            "restriction": {
                "type": "string",
                "description": "The dietary restriction (e.g., 'vegetarian', 'vegan', 'gluten-free', 'dairy-free')"
            }
        }
    }
]

def build_compact_menu(menu_items: List[Dict]) -> List[Dict]:
    """Build compact menu catalog with just essential info"""
    compact_items = []
    
    for item in menu_items:
        # Essential info only
        compact_item = {
            "name": item.get('dish', 'Unknown'),
            "category": item.get('subcategory') or item.get('category', 'Other'),
            "price": item.get('price', 0)
        }
        
        # Add dietary indicators if present
        dietary = []
        
        # Check ingredients for dietary info
        ingredients = ' '.join(item.get('ingredients', [])).lower()
        allergens = [a.lower() for a in item.get('allergens', [])]
        
        if not any(meat in ingredients for meat in ['chicken', 'beef', 'pork', 'lamb', 'meat', 'bacon', 'fish', 'shrimp', 'lobster']):
            dietary.append("vegetarian")
        
        if 'gluten' not in allergens and 'pasta' not in ingredients and 'bread' not in ingredients:
            dietary.append("gluten-free")
            
        if dietary:
            compact_item["dietary"] = dietary
            
        compact_items.append(compact_item)
    
    return compact_items

def execute_menu_tool(tool_name: str, parameters: Dict, menu_items: List[Dict]) -> Dict:
    """Execute a menu query tool and return results"""
    
    if tool_name == "get_dish_details":
        dish_name = parameters.get("dish_name", "").lower()
        
        for item in menu_items:
            if dish_name in item.get('dish', '').lower():
                return {
                    "found": True,
                    "dish": {
                        "name": item.get('dish'),
                        "description": item.get('description', 'No description available'),
                        "ingredients": item.get('ingredients', []),
                        "allergens": item.get('allergens', []),
                        "price": item.get('price', 0),
                        "category": item.get('subcategory') or item.get('category', 'Other'),
                        "photo_url": item.get('photo_url')
                    }
                }
        
        return {"found": False, "error": f"Dish '{parameters.get('dish_name')}' not found"}
    
    elif tool_name == "search_by_ingredient":
        ingredient = parameters.get("ingredient", "").lower()
        results = []
        
        for item in menu_items:
            ingredients = [ing.lower() for ing in item.get('ingredients', [])]
            if any(ingredient in ing for ing in ingredients):
                results.append({
                    "name": item.get('dish'),
                    "price": item.get('price', 0),
                    "ingredients": item.get('ingredients', [])
                })
        
        return {
            "found": len(results),
            "dishes": results[:10]  # Limit to 10
        }
    
    elif tool_name == "filter_by_category":
        category = parameters.get("category", "").lower()
        results = []
        
        for item in menu_items:
            item_cat = (item.get('subcategory') or item.get('category', '')).lower()
            if category in item_cat:
                results.append({
                    "name": item.get('dish'),
                    "price": item.get('price', 0)
                })
        
        return {
            "found": len(results),
            "category": category,
            "dishes": results
        }
    
    elif tool_name == "check_dietary_restriction":
        restriction = parameters.get("restriction", "").lower()
        results = []
        
        for item in menu_items:
            ingredients = ' '.join(item.get('ingredients', [])).lower()
            allergens = [a.lower() for a in item.get('allergens', [])]
            suitable = True
            
            if restriction == "vegetarian":
                meats = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'bacon', 'fish', 'shrimp', 'lobster']
                if any(meat in ingredients for meat in meats):
                    suitable = False
                    
            elif restriction == "vegan":
                animal_products = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'bacon', 'fish', 'shrimp', 
                                 'lobster', 'milk', 'cream', 'butter', 'cheese', 'egg']
                if any(prod in ingredients for prod in animal_products):
                    suitable = False
                    
            elif restriction == "gluten-free":
                if 'gluten' in allergens or any(g in ingredients for g in ['pasta', 'bread', 'flour']):
                    suitable = False
                    
            elif restriction in allergens:
                suitable = False
            
            if suitable:
                results.append({
                    "name": item.get('dish'),
                    "price": item.get('price', 0),
                    "category": item.get('subcategory') or item.get('category', 'Other')
                })
        
        return {
            "found": len(results),
            "restriction": restriction,
            "dishes": results[:15]  # Limit to 15
        }
    
    return {"error": f"Unknown tool: {tool_name}"}

def mia_chat_service_full_menu_compact(req: ChatRequest, db: Session) -> ChatResponse:
    """Full menu service with compact catalog and tool support"""
    
    try:
        # Get restaurant/business
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            business = db.query(models.Business).filter(
                models.Business.business_id == req.restaurant_id
            ).first()
            if business:
                restaurant = models.Restaurant(
                    restaurant_id=business.business_id,
                    restaurant_name=business.business_name,
                    data=business.data or {}
                )
            else:
                return ChatResponse(answer="Restaurant not found")
        
        menu_data = restaurant.data or {}
        business_name = menu_data.get('restaurant_name') or restaurant.restaurant_name
        menu_items = menu_data.get('menu', [])
        
        # Get customer memory
        memory_service = CustomerMemoryService(db)
        conversation_history = memory_service.get_conversation_with_name(
            req.client_id, 
            req.restaurant_id
        )
        
        # Build compact menu
        compact_menu = build_compact_menu(menu_items)
        
        # Check if this is a tool result response
        if hasattr(req, 'tool_result') and req.tool_result:
            # MIA is responding with a tool call, execute it
            tool_call = req.tool_result
            tool_result = execute_menu_tool(
                tool_call.get('name'),
                tool_call.get('parameters', {}),
                menu_items
            )
            
            # Send tool result back to MIA
            mia = MiaDirectAPI()
            response = mia.send_tool_result(
                original_prompt=req.message,
                tool_call=tool_call,
                tool_result=tool_result,
                context={
                    "business_name": business_name,
                    "conversation_history": conversation_history
                }
            )
            
            answer = response.get('response', "I couldn't process that request.")
            
        else:
            # Regular message - send with tools
            system_prompt = f"""You are Maria, a friendly and knowledgeable server at {business_name}.

{conversation_history}

Here's our current menu (compact view):
{json.dumps(compact_menu, indent=2)}

When customers ask about specific dishes, ingredients, dietary restrictions, or want detailed information, 
use the provided tools to fetch that information. The tools will give you complete details including 
descriptions, full ingredient lists, and allergen information.

Important guidelines:
- Always be warm, professional, and helpful
- Use tools when customers need specific information not in the compact menu
- Recommend dishes based on customer preferences
- Mention prices when discussing specific items
- Be knowledgeable about ingredients and dietary restrictions"""

            # Send to MIA with tools
            mia = MiaDirectAPI()
            response = mia.send_message_with_tools(
                prompt=req.message,
                system_prompt=system_prompt,
                tools=MENU_QUERY_TOOLS,
                context={
                    "business_name": business_name,
                    "menu_items": [item["name"] for item in compact_menu]
                }
            )
            
            # Check if MIA wants to use a tool
            if response.get('tool_call'):
                # Execute the tool
                tool_result = execute_menu_tool(
                    response['tool_call']['name'],
                    response['tool_call'].get('parameters', {}),
                    menu_items
                )
                
                # Get final response with tool result
                final_response = mia.send_tool_result(
                    original_prompt=req.message,
                    tool_call=response['tool_call'],
                    tool_result=tool_result,
                    context={
                        "business_name": business_name,
                        "conversation_history": conversation_history
                    }
                )
                
                answer = final_response.get('response', response.get('response', "I'll help you with that."))
            else:
                answer = response.get('response', "I couldn't understand your request.")
        
        # Save the interaction
        memory_service.save_interaction(
            client_id=req.client_id,
            restaurant_id=req.restaurant_id,
            user_message=req.message,
            ai_response=answer
        )
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in compact full menu service: {e}")
        return ChatResponse(answer="I'm having trouble accessing the menu information right now.")