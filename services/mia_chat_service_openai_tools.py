"""
MIA Chat Service with Proper OpenAI Tools API
Uses vLLM's OpenAI-compatible interface for tool calling
"""
import json
import logging
import requests
from typing import Dict, List, Optional, Tuple, Any
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse
from services.customer_memory_service import CustomerMemoryService
from services.mia_chat_service_hybrid import get_or_create_client
import os

logger = logging.getLogger(__name__)

# MIA Backend URL - should be the vLLM OpenAI-compatible endpoint
MIA_OPENAI_URL = os.getenv("MIA_OPENAI_URL", "http://localhost:8000/v1")

# Tool definitions in OpenAI format
TOOLS = [
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
                        "description": "The term to search for"
                    },
                    "search_type": {
                        "type": "string",
                        "enum": ["ingredient", "category", "name"],
                        "description": "Type of search to perform"
                    }
                },
                "required": ["search_term"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_dish_details",
            "description": "Get complete details about a specific dish",
            "parameters": {
                "type": "object",
                "properties": {
                    "dish": {
                        "type": "string",
                        "description": "Name of the dish"
                    }
                },
                "required": ["dish"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "filter_by_dietary",
            "description": "Find dishes suitable for dietary restrictions",
            "parameters": {
                "type": "object",
                "properties": {
                    "diet": {
                        "type": "string",
                        "description": "Dietary restriction (e.g., vegetarian, vegan, gluten-free)"
                    }
                },
                "required": ["diet"]
            }
        }
    }
]

def classify_intent(message: str) -> Tuple[bool, Optional[str]]:
    """
    Classify user intent and determine if tools should be used
    Returns: (should_use_tools, forced_tool_name)
    """
    message_lower = message.lower()
    
    # Food/menu related keywords that should trigger tools
    food_keywords = [
        'menu', 'food', 'dish', 'meal', 'eat', 'hungry', 'order',
        'fish', 'meat', 'chicken', 'beef', 'pork', 'seafood', 'pasta',
        'vegetarian', 'vegan', 'gluten', 'dairy', 'allergy',
        'recommend', 'suggestion', 'popular', 'special',
        'ingredient', 'contain', 'made with', 'what do you have'
    ]
    
    # Greetings and non-food interactions
    non_food_keywords = [
        'hello', 'hi', 'hey', 'good morning', 'good evening',
        'thank', 'thanks', 'bye', 'goodbye', 'see you',
        'how are you', 'nice', 'great', 'weather'
    ]
    
    # Check for non-food first (higher priority)
    if any(keyword in message_lower for keyword in non_food_keywords) and \
       not any(keyword in message_lower for keyword in food_keywords):
        return False, None
    
    # Check for food/menu queries
    if any(keyword in message_lower for keyword in food_keywords):
        # Force search_menu_items for general food queries
        if any(word in message_lower for word in ['want', 'have', 'show', 'what', 'menu']):
            return True, "search_menu_items"
        # Could extend to force get_dish_details if specific dish mentioned
        return True, None
    
    # Default: no tools for unclear messages
    return False, None

def execute_tool_function(name: str, arguments: Dict, menu_items: List[Dict]) -> Dict:
    """Execute the actual tool function and return results"""
    try:
        if name == "search_menu_items":
            search_term = arguments.get("search_term", "").lower()
            search_type = arguments.get("search_type", "ingredient")
            results = []
            
            for item in menu_items:
                match = False
                item_name = (item.get('dish') or item.get('name', '')).lower()
                
                if search_type == "name":
                    if search_term in item_name:
                        match = True
                elif search_type == "ingredient":
                    # Enhanced search for common food groups
                    ingredients = [str(ing).lower() for ing in item.get('ingredients', [])]
                    
                    # Expand search for related terms
                    if search_term == "fish":
                        related = ["fish", "salmon", "seafood", "tuna", "cod", "halibut", "sea bass"]
                        if any(term in item_name for term in related) or \
                           any(any(term in ing for term in related) for ing in ingredients):
                            match = True
                    elif search_term == "meat":
                        related = ["meat", "beef", "steak", "chicken", "pork", "lamb", "veal"]
                        if any(term in item_name for term in related) or \
                           any(any(term in ing for term in related) for ing in ingredients):
                            match = True
                    else:
                        if search_term in item_name or any(search_term in ing for ing in ingredients):
                            match = True
                elif search_type == "category":
                    category = (item.get('subcategory') or item.get('category', '')).lower()
                    if search_term in category:
                        match = True
                
                if match:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "description": item.get('description', '')[:100] + "..." if item.get('description') else ""
                    })
            
            return {
                "found": len(results),
                "items": results[:10]  # Limit to 10 items
            }
        
        elif name == "get_dish_details":
            dish_name = arguments.get("dish", "").lower()
            
            for item in menu_items:
                item_name = (item.get('dish') or item.get('name', '')).lower()
                if dish_name in item_name or item_name in dish_name:
                    return {
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', ''),
                        "description": item.get('description', ''),
                        "ingredients": item.get('ingredients', []),
                        "allergens": item.get('allergens', [])
                    }
            
            return {"error": f"Dish '{arguments.get('dish')}' not found"}
        
        elif name == "filter_by_dietary":
            diet = arguments.get("diet", "").lower()
            results = []
            
            for item in menu_items:
                suitable = True
                ingredients = [i.lower() for i in item.get('ingredients', [])]
                allergens = [a.lower() for a in item.get('allergens', [])]
                
                if diet in ["vegetarian", "veg"]:
                    meat_words = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'bacon', 'fish', 'seafood']
                    if any(meat in ' '.join(ingredients) for meat in meat_words):
                        suitable = False
                
                elif diet == "vegan":
                    animal = ['chicken', 'beef', 'pork', 'lamb', 'meat', 'fish', 'seafood', 
                             'cheese', 'milk', 'cream', 'butter', 'egg', 'honey']
                    if any(a in ' '.join(ingredients) for a in animal):
                        suitable = False
                
                elif "gluten" in diet:
                    if "gluten" in allergens or any(g in ' '.join(ingredients) 
                                                   for g in ['pasta', 'bread', 'flour', 'wheat']):
                        suitable = False
                
                if suitable:
                    results.append({
                        "name": item.get('dish') or item.get('name', ''),
                        "price": item.get('price', '')
                    })
            
            return {
                "diet": diet,
                "found": len(results),
                "items": results[:15]
            }
    
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        return {"error": str(e)}

def call_mia_with_tools(messages: List[Dict], tools: Optional[List] = None, 
                       tool_choice: Optional[Any] = None, temperature: float = 0.0) -> Dict:
    """Call MIA using OpenAI-compatible API"""
    try:
        request_data = {
            "model": "qwen2.5-7b-instruct-awq",  # or whatever model name vLLM expects
            "messages": messages,
            "temperature": temperature,
            "max_tokens": 300
        }
        
        if tools:
            request_data["tools"] = tools
            if tool_choice:
                request_data["tool_choice"] = tool_choice
        
        logger.info(f"Calling MIA with tools: {bool(tools)}, tool_choice: {tool_choice}")
        
        response = requests.post(
            f"{MIA_OPENAI_URL}/chat/completions",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            raise Exception(f"API error: {response.status_code}")
    
    except Exception as e:
        logger.error(f"Error calling MIA: {e}")
        raise

def generate_response_openai_tools(req: ChatRequest, db: Session) -> ChatResponse:
    """Generate response using proper OpenAI Tools API"""
    try:
        logger.info(f"OpenAI Tools - Request from {req.client_id}: {req.message}")
        
        # Get restaurant and menu data
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant or not restaurant.data:
            return ChatResponse(answer="I'm sorry, but I couldn't find the restaurant information.")
        
        menu_items = restaurant.data.get('menu', [])
        restaurant_name = restaurant.data.get('restaurant_name', 'Bella Vista Restaurant')
        
        # Get or create client
        get_or_create_client(db, req.client_id, req.restaurant_id)
        
        # Get customer profile
        client_id_str = str(req.client_id)
        customer_profile = db.query(models.CustomerProfile).filter(
            models.CustomerProfile.client_id == client_id_str,
            models.CustomerProfile.restaurant_id == req.restaurant_id
        ).first()
        
        # Get recent conversation history
        recent_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.restaurant_id == req.restaurant_id,
            models.ChatMessage.client_id == req.client_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(5).all()
        
        # Build message history for OpenAI format
        messages = [
            {
                "role": "system",
                "content": f"You are Maria, a friendly server at {restaurant_name}. "
                          f"Be warm, helpful, and concise. Use tool results when provided to give accurate information."
            }
        ]
        
        # Add conversation history
        for msg in reversed(recent_messages[1:]):  # Skip current message
            if msg.sender_type == "client":
                messages.append({"role": "user", "content": msg.message})
            else:
                messages.append({"role": "assistant", "content": msg.message})
        
        # Add current message
        messages.append({"role": "user", "content": req.message})
        
        # Classify intent
        use_tools, forced_tool = classify_intent(req.message)
        
        if use_tools:
            # STEP 1: Call with tools enabled
            tool_choice = {"type": "function", "function": {"name": forced_tool}} if forced_tool else "auto"
            
            response1 = call_mia_with_tools(
                messages=messages,
                tools=TOOLS,
                tool_choice=tool_choice,
                temperature=0.0  # Deterministic for tools
            )
            
            # Extract tool calls from response
            choice = response1.get("choices", [{}])[0]
            message = choice.get("message", {})
            tool_calls = message.get("tool_calls", [])
            
            if tool_calls:
                logger.info(f"Model made {len(tool_calls)} tool calls")
                
                # STEP 2: Execute tools and prepare results
                messages.append(message)  # Add assistant's tool call message
                
                for tool_call in tool_calls:
                    function = tool_call.get("function", {})
                    name = function.get("name")
                    arguments = json.loads(function.get("arguments", "{}"))
                    
                    logger.info(f"Executing tool: {name} with args: {arguments}")
                    result = execute_tool_function(name, arguments, menu_items)
                    
                    # Add tool result as tool message
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call.get("id"),
                        "content": json.dumps(result)
                    })
                
                # STEP 3: Final call without tools to get natural response
                response2 = call_mia_with_tools(
                    messages=messages,
                    tools=None,  # No tools for final response
                    temperature=0.0
                )
                
                final_message = response2.get("choices", [{}])[0].get("message", {})
                response_text = final_message.get("content", "I found some options for you!")
            else:
                # Model didn't use tools despite being offered
                logger.warning("Model didn't use tools when expected")
                response_text = message.get("content", "Let me help you with our menu.")
        else:
            # No tools needed - direct response
            response1 = call_mia_with_tools(
                messages=messages,
                tools=None,
                temperature=0.7  # More variety for casual chat
            )
            
            choice = response1.get("choices", [{}])[0]
            response_text = choice.get("message", {}).get("content", "Hello! How can I help you?")
        
        # Save AI response to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=response_text
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(answer=response_text)
    
    except Exception as e:
        logger.error(f"Error in OpenAI tools service: {e}", exc_info=True)
        db.rollback()
        return ChatResponse(answer="I apologize, I'm having trouble accessing the menu right now. Our popular items include the Grilled Salmon and Ribeye Steak.")