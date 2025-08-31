"""
MIA Chat Service with Tool/Function Calling
Allows MIA to query the database itself when needed
"""
import json
import requests
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse
import logging

logger = logging.getLogger(__name__)

# Define available tools for MIA
AVAILABLE_TOOLS = [
    {
        "name": "search_menu_items",
        "description": "Search for menu items by name, ingredient, or category",
        "parameters": {
            "type": "object",
            "properties": {
                "search_term": {
                    "type": "string",
                    "description": "What to search for (e.g., 'pasta', 'tomato', 'vegetarian')"
                },
                "search_type": {
                    "type": "string",
                    "enum": ["name", "ingredient", "category", "allergen"],
                    "description": "Type of search to perform"
                }
            },
            "required": ["search_term"]
        }
    },
    {
        "name": "get_dish_details",
        "description": "Get full details about a specific dish",
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
    },
    {
        "name": "get_menu_categories",
        "description": "Get list of all menu categories",
        "parameters": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "filter_by_dietary",
        "description": "Find dishes matching dietary restrictions",
        "parameters": {
            "type": "object",
            "properties": {
                "restrictions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of dietary restrictions (e.g., ['vegetarian', 'gluten-free'])"
                }
            },
            "required": ["restrictions"]
        }
    }
]

def execute_tool(tool_name: str, parameters: Dict, db: Session, restaurant_id: str) -> Dict:
    """Execute a tool call and return results"""
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant or not restaurant.data:
        return {"error": "Restaurant not found"}
    
    menu_items = restaurant.data.get('menu', [])
    
    if tool_name == "search_menu_items":
        search_term = parameters.get("search_term", "").lower()
        search_type = parameters.get("search_type", "ingredient")
        results = []
        
        for item in menu_items:
            if search_type == "name":
                if search_term in item.get('dish', '').lower():
                    results.append(item)
            elif search_type == "ingredient":
                ingredients = item.get('ingredients', [])
                if any(search_term in ing.lower() for ing in ingredients):
                    results.append(item)
            elif search_type == "category":
                if search_term in (item.get('subcategory', '') or item.get('category', '')).lower():
                    results.append(item)
            elif search_type == "allergen":
                allergens = item.get('allergens', [])
                if any(search_term in allerg.lower() for allerg in allergens):
                    results.append(item)
        
        return {
            "found": len(results),
            "items": results[:10]  # Limit to 10 items
        }
    
    elif tool_name == "get_dish_details":
        dish_name = parameters.get("dish_name", "").lower()
        for item in menu_items:
            if dish_name in item.get('dish', '').lower():
                return {"dish": item}
        return {"error": f"Dish '{dish_name}' not found"}
    
    elif tool_name == "get_menu_categories":
        categories = set()
        for item in menu_items:
            cat = item.get('subcategory') or item.get('category', 'Other')
            categories.add(cat)
        return {"categories": sorted(list(categories))}
    
    elif tool_name == "filter_by_dietary":
        restrictions = parameters.get("restrictions", [])
        results = []
        
        for item in menu_items:
            allergens = [a.lower() for a in item.get('allergens', [])]
            ingredients = [i.lower() for i in item.get('ingredients', [])]
            
            # Check if item matches dietary restrictions
            is_suitable = True
            for restriction in restrictions:
                if restriction.lower() == "vegetarian":
                    meat_words = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'bacon']
                    if any(meat in ' '.join(ingredients) for meat in meat_words):
                        is_suitable = False
                elif restriction.lower() == "gluten-free":
                    if 'gluten' in allergens or 'pasta' in ' '.join(ingredients):
                        is_suitable = False
                elif restriction.lower() in allergens:
                    is_suitable = False
            
            if is_suitable:
                results.append(item)
        
        return {
            "found": len(results),
            "items": results[:10]
        }
    
    return {"error": f"Unknown tool: {tool_name}"}

def mia_chat_service_with_tools(req: ChatRequest, db: Session) -> ChatResponse:
    """MIA chat service that can use tools to query data"""
    
    try:
        # Get restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="Restaurant not found")
        
        business_name = restaurant.data.get('restaurant_name', req.restaurant_id)
        
        # Build system prompt with tool descriptions
        system_prompt = f"""You are Maria, a friendly server at {business_name}.

You have access to the following tools to help answer customer questions:

{json.dumps(AVAILABLE_TOOLS, indent=2)}

When you need information about the menu, use these tools by responding with:
TOOL_CALL: {{"name": "tool_name", "parameters": {{"param": "value"}}}}

After receiving tool results, provide a natural response to the customer.

Important:
- Always search for menu items when customers mention ingredients or preferences
- Get full dish details when customers ask about specific dishes
- Check dietary restrictions when customers mention allergies
- Be proactive in using tools to provide accurate information
"""
        
        # This is where it gets interesting - we need to:
        # 1. Send initial prompt to MIA
        # 2. Check if MIA wants to use a tool
        # 3. Execute the tool
        # 4. Send results back to MIA
        # 5. Get final response
        
        # For now, this is a demonstration of the structure
        # Full implementation would require MIA to support function calling
        
        return ChatResponse(
            answer="This service requires MIA to support function/tool calling. "
                   "Currently showing structure for future implementation."
        )
        
    except Exception as e:
        logger.error(f"Error in tool-based service: {e}")
        return ChatResponse(answer="I'm having trouble accessing the information.")