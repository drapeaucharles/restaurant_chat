"""
MIA Chat Service with Internal Tool Flow V5
- Concise, natural responses
- No repetitive greetings
- Better conversation continuity
- Smart context awareness
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

def create_menu_summary(menu_items: List[Dict]) -> str:
    """Create a concise summary of menu items for simple flow context"""
    if not menu_items:
        return "No menu items available."
    
    # Group by category
    categories = {}
    for item in menu_items:
        cat = item.get('category', 'Other')
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(item)
    
    # Build summary
    summary = "Available dishes:\n"
    for cat, items in categories.items():
        summary += f"\n{cat}:\n"
        for item in items[:10]:  # Limit to 10 per category to avoid token explosion
            name = item.get('dish') or item.get('name', 'Unknown')
            price = item.get('price', 'Price not set')
            allergens = item.get('allergens', [])
            allergen_str = f" (contains: {', '.join(allergens)})" if allergens else ""
            summary += f"- {name}: {price}{allergen_str}\n"
        if len(items) > 10:
            summary += f"- ... and {len(items) - 10} more {cat} items\n"
    
    return summary

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
    "update_allergy_add": {
        "description": "Add a new allergy to customer profile",
        "when_to_use": "Customer mentions a new allergy or dietary restriction",
        "schema": {
            "type": "function",
            "function": {
                "name": "update_customer_allergies",
                "description": "Add allergies to customer profile",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["add"], "default": "add"},
                        "allergies": {"type": "array", "items": {"type": "string"}},
                        "reason": {"type": "string", "description": "Why adding (e.g., 'customer mentioned allergy')"}
                    },
                    "required": ["allergies"]
                }
            }
        }
    },
    "update_allergy_remove": {
        "description": "Remove an allergy from customer profile",
        "when_to_use": "Customer says they're NOT allergic, it was a mistake, or for someone else",
        "schema": {
            "type": "function",
            "function": {
                "name": "update_customer_allergies",
                "description": "Remove allergies from customer profile",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "action": {"type": "string", "enum": ["remove"], "default": "remove"},
                        "allergies": {"type": "array", "items": {"type": "string"}},
                        "reason": {"type": "string", "description": "Why removing (e.g., 'not allergic', 'was a joke', 'for someone else')"}
                    },
                    "required": ["allergies", "reason"]
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

def get_customer_profile(db: Session, client_id: str, restaurant_id: str) -> Optional[Any]:
    """Get or create customer profile with allergies and preferences"""
    try:
        from services.customer_memory_service import CustomerMemoryService
        profile = CustomerMemoryService.get_or_create_profile(db, client_id, restaurant_id)
        return profile
    except Exception as e:
        logger.warning(f"Could not load customer profile: {e}")
        return None

def get_chat_history(db: Session, client_id: str, restaurant_id: str, limit: int = 5) -> List[Dict]:
    """Get recent chat history for context"""
    try:
        # Get last N messages between this client and restaurant
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.client_id == client_id,
            models.ChatMessage.restaurant_id == restaurant_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(limit * 2).all()  # Get double to include AI responses
        
        # Format for context (newest first, then reverse for chronological order)
        history = []
        for msg in reversed(messages):
            history.append({
                "role": "user" if msg.sender_type == "customer" else "assistant",
                "message": msg.message
            })
        
        return history[-limit:]  # Keep only last N exchanges
    except Exception as e:
        logger.warning(f"Could not load chat history: {e}")
        return []

def get_context_type(customer_profile: Any, message: str) -> Tuple[str, Dict]:
    """Determine context type based on customer profile and message"""
    context_data = {}
    message_lower = message.lower()
    
    # Check for allergy correction/removal patterns
    removal_patterns = [
        'not allergic', 'no allergy', "don't have allergy", 
        'can eat', 'was a joke', 'made a mistake',
        'for my friend', 'for someone else', "isn't for me",
        'actually i can', 'show me with'
    ]
    
    if any(pattern in message_lower for pattern in removal_patterns):
        # This is likely an allergy correction
        return "allergy_correction", context_data
    
    # Check if customer has allergies or dietary restrictions
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary_restrictions = getattr(customer_profile, 'dietary_restrictions', []) or []
        all_restrictions = allergies + dietary_restrictions
        
        if all_restrictions:
            context_data = {
                'allergens': allergies,
                'dietary_preferences': dietary_restrictions,
                'all_restrictions': all_restrictions,
                'strict_mode': True
            }
            # If asking for items WITH their allergen, it might be a correction
            if any(allergen.lower() in message_lower and 'with' in message_lower for allergen in allergies):
                return "allergy_correction", context_data
            return "allergen_safety", context_data
    
    # Check message for allergy/dietary mentions
    allergen_keywords = ['allerg', 'intolerant', 'can\'t eat', 'avoid', 'free from']
    dietary_keywords = ['vegan', 'vegetarian', 'gluten', 'dairy', 'nut']
    
    if any(keyword in message_lower for keyword in allergen_keywords + dietary_keywords):
        return "allergen_query", context_data
    
    return "general", context_data

def build_phase1_prompt(message: str, customer_profile: Any = None, chat_history: List[Dict] = None) -> str:
    """Build Phase 1 prompt with customer context and history"""
    prompt = "Analyze this conversation and select tools for the latest message.\n\n"
    
    # Add chat history if available
    if chat_history and len(chat_history) > 0:
        prompt += "CONVERSATION HISTORY:\n"
        for msg in chat_history[:-1]:  # All except current message
            role = "Customer" if msg["role"] == "user" else "You"
            prompt += f"{role}: {msg['message']}\n"
        prompt += "\n"
    
    prompt += f"""CURRENT MESSAGE: "{message}"

"""
    
    # Add customer context if available
    if customer_profile:
        allergies = getattr(customer_profile, 'allergies', []) or []
        dietary = getattr(customer_profile, 'dietary_restrictions', []) or []
        
        if allergies or dietary:
            prompt += f"""IMPORTANT CUSTOMER INFO:
- Allergies: {', '.join(allergies) if allergies else 'None'}
- Dietary Restrictions: {', '.join(dietary) if dietary else 'None'}
⚠️ CRITICAL: This customer has allergies/restrictions!
You MUST include the appropriate filter tools for their safety:
{' + filter_nut_free if nuts allergy' if 'nuts' in allergies else ''}
{' + filter_dairy_free if dairy allergy' if 'dairy' in allergies else ''}
{' + filter_gluten_free if gluten allergy' if 'gluten' in allergies else ''}
Always include allergy filters PLUS any other relevant tools!

"""
    
    prompt += """AVAILABLE TOOLS:
- get_dish_details: Get complete information about a specific dish (ingredients, allergens, price)
- search_menu_by_category: Search menu items by category (pasta, seafood, appetizers, etc.)
- search_menu_by_ingredient: Search menu items containing specific ingredients
- filter_vegetarian: Show only vegetarian dishes
- filter_vegan: Show only vegan dishes
- filter_gluten_free: Show only gluten-free dishes
- filter_nut_free: Show only nut-free dishes
- filter_dairy_free: Show only dairy-free dishes
- update_allergy_add: Add a new allergy to customer profile
- update_allergy_remove: Remove an allergy from customer profile

RULES:
0. Always check allergies first → apply all relevant filter tools.
1. Respond with ONLY tool names from the list above.
2. If multiple tools apply, include all of them.
3. Return as JSON array: ["tool_name1", "tool_name2"].
4. For allergies AND menu search, include both.
5. If no tools are needed (e.g. "thanks", "ok"), return: ["no_tool_needed"].

EXAMPLES:
- "I'm vegan and want pasta" → ["filter_vegan", "search_menu_by_category"]
- "Tell me about the carbonara" → ["get_dish_details"]
- "What's the price of the carbonara?" → ["get_dish_details"]
- "Show me seafood dishes, I'm allergic to nuts" → ["filter_nut_free", "search_menu_by_category"]
- "Actually I'm not allergic to dairy" → ["update_allergy_remove"]
- "Add shellfish to my allergies" → ["update_allergy_add"]
- "Thanks" → ["no_tool_needed"]

Respond with ONLY the JSON array of tool names."""
    
    return prompt

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
                    "description": item.get('description', '')[:100],
                    "allergens": item.get('allergens', [])
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
    
    elif actual_function == "update_customer_allergies":
        action = parameters.get("action", "add")
        allergies = parameters.get("allergies", [])
        reason = parameters.get("reason", "")
        
        return {
            "tool": tool_name,
            "action": action,
            "allergies": allergies,
            "reason": reason,
            "message": f"Will {action} allergies: {', '.join(allergies)}"
        }
    
    return {"error": "Tool execution not implemented"}

def build_final_prompt(message: str, tool_results: List[Dict], restaurant_name: str, 
                      customer_profile: Any, context_type: str, context_data: Dict,
                      chat_history: List[Dict] = None) -> str:
    """Build final prompt with full context and conversation history"""
    
    # Start with context-specific prompt
    if context_type == "allergen_safety":
        prompt = f"""You are Maria, a safety-conscious server at {restaurant_name}.

CRITICAL SAFETY MODE - Customer has restrictions: {', '.join(context_data.get('all_restrictions', []))}

MANDATORY SAFETY RULES:
1. ONLY recommend items that are 100% safe for ALL restrictions
2. ALWAYS mention their specific restrictions when suggesting dishes
3. If unsure about ingredients, say so - never guess
4. Double-check allergen information in the tool results

"""
    else:
        prompt = f"""You are Maria, a warm and knowledgeable server at {restaurant_name}.

"""
    
    # Add conversation history for continuity
    if chat_history and len(chat_history) > 1:
        # Count how many times we've interacted
        interaction_count = sum(1 for msg in chat_history if msg["role"] == "assistant")
        
        prompt += "CONVERSATION SO FAR:\n"
        for msg in chat_history[:-1]:  # All except current message
            if msg["role"] == "user":
                prompt += f"Customer: {msg['message']}\n"
            else:
                prompt += f"You: {msg['message']}\n"
        prompt += f"\n[This is message #{interaction_count + 1} - NO MORE GREETINGS]\n"
    
    prompt += f"""Customer: "{message}"
"""
    
    # Add customer profile info
    if customer_profile:
        name = getattr(customer_profile, 'name', None)
        if name:
            prompt += f"\nReturning customer: {name}\n"
    
    # Add tool results
    prompt += "\nINFORMATION FROM OUR MENU:\n"
    for result in tool_results:
        prompt += f"\n{json.dumps(result, indent=2)}\n"
    
    # Add response guidelines based on context
    if context_type == "allergen_safety":
        prompt += """
CRITICAL GUIDELINES:
- Be CONCISE - 2-3 sentences max per dish
- NEVER say "Hello" if already greeted in this conversation
- Safety first: Only recommend 100% safe items
- Format: "The [dish] ($X) is safe - it's [brief description]"
"""
    elif context_type == "allergy_correction":
        prompt += """
RESPONSE GUIDELINES:
- Be BRIEF - acknowledge in 1 sentence
- Suggest 1-2 newly available dishes
- No lengthy explanations
"""
    else:
        prompt += """
RESPONSE GUIDELINES:
- Keep it SHORT - max 3-4 sentences total
- NEVER say "Hello" if already greeted
- Answer the specific question asked
- One dish = one sentence with price
- Skip pleasantries if mid-conversation
"""
    
    prompt += "\nRespond naturally and CONCISELY:"
    
    return prompt

def generate_response_internal_tools_v5(req: Any, db: Session) -> Any:
    """Three-phase flow with proper context preservation"""
    from schemas.chat import ChatResponse
    
    try:
        logger.info(f"=== Internal Tools V5 (Concise) - Restaurant: {req.restaurant_id} ===")
        
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter_by(
            restaurant_id=req.restaurant_id
        ).first()
        
        if not restaurant:
            # Try businesses table
            from sqlalchemy import text
            result = db.execute(
                text("SELECT data FROM businesses WHERE business_id = :id"),
                {"id": req.restaurant_id}
            ).fetchone()
            
            if result:
                restaurant_data = result[0] if isinstance(result[0], dict) else json.loads(result[0])
            else:
                return ChatResponse(answer="Restaurant not found", response_id=None, confidence_score=0.0)
        else:
            try:
                restaurant_data = restaurant.data if isinstance(restaurant.data, dict) else json.loads(restaurant.data)
            except:
                restaurant_data = {}
        
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        menu_items = restaurant_data.get('menu', [])
        
        # Load customer profile
        customer_profile = get_customer_profile(db, req.client_id, req.restaurant_id)
        logger.info(f"Customer profile loaded: {customer_profile is not None}")
        
        # Load chat history
        chat_history = get_chat_history(db, req.client_id, req.restaurant_id, limit=3)
        logger.info(f"Chat history loaded: {len(chat_history)} messages")
        
        # Determine context type
        context_type, context_data = get_context_type(customer_profile, req.message)
        logger.info(f"Context type: {context_type}")
        
        # === PHASE 1: Tool Selection with Context ===
        logger.info("PHASE 1: Tool selection with customer context")
        phase1_prompt = build_phase1_prompt(req.message, customer_profile, chat_history)
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": phase1_prompt,
                "max_tokens": 100,
                "temperature": 0.1
            },
            timeout=30
        )
        
        if response.status_code != 200:
            return ChatResponse(answer="I'm having trouble understanding. Please try again.", response_id=None, confidence_score=0.0)
        
        # Parse tool selection
        selection_text = response.json().get("response", "").strip()
        try:
            if "[" in selection_text and "]" in selection_text:
                start = selection_text.find("[")
                end = selection_text.rfind("]") + 1
                selected_tools = json.loads(selection_text[start:end])
            else:
                selected_tools = ["no_tool_needed"]
        except:
            selected_tools = ["no_tool_needed"]
        
        logger.info(f"Selected tools: {selected_tools}")
        
        # IMPORTANT: If customer has allergies, ensure appropriate allergy tools are included
        # BUT not if they're correcting/removing allergies
        if context_type == "allergen_safety" and context_data.get('allergens'):
            allergen_tools_map = {
                'nuts': 'filter_nut_free',
                'dairy': 'filter_dairy_free',
                'gluten': 'filter_gluten_free'
            }
            
            for allergen in context_data['allergens']:
                tool_name = allergen_tools_map.get(allergen.lower())
                if tool_name and tool_name not in selected_tools:
                    selected_tools.append(tool_name)
                    logger.info(f"Auto-added {tool_name} due to {allergen} allergy")
        
        # If no tools needed, generate contextual response
        if selected_tools == ["no_tool_needed"]:
            # Create a menu summary to include in simple flow
            menu_summary = create_menu_summary(menu_items)
            
            # Build prompt with history
            if context_type == "allergen_safety":
                simple_prompt = f"""You are Maria at {restaurant_name}.
Customer with restrictions ({', '.join(context_data.get('all_restrictions', []))})

"""
            elif context_type == "allergy_correction":
                simple_prompt = f"""You are Maria at {restaurant_name}.
The customer is correcting or updating their allergy information.

"""
            else:
                simple_prompt = f"""You are Maria at {restaurant_name}.

"""
            
            # Add conversation history
            if chat_history and len(chat_history) > 1:
                simple_prompt += "Conversation so far:\n"
                for msg in chat_history[:-1]:
                    role = "Customer" if msg["role"] == "user" else "You"
                    simple_prompt += f"{role}: {msg['message']}\n"
                simple_prompt += "\n"
            
            # ADD MENU INFORMATION
            simple_prompt += f"""\nMENU INFORMATION:
{menu_summary}
"""
            
            # Check if this is first message
            is_greeting = chat_history is None or len(chat_history) <= 1
            
            simple_prompt += f"""\nCustomer: "{req.message}"

IMPORTANT: 
- Be CONCISE - max 2-3 sentences
- {"Greet warmly ONCE" if is_greeting else "NO greeting - continue conversation"}
- Answer their specific question directly
- USE ACTUAL MENU PRICES AND ITEMS from the menu information above
- NEVER make up dishes or prices that aren't in the menu"""
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={"message": simple_prompt, "max_tokens": 200},
                timeout=30
            )
            
            if response.status_code == 200:
                return ChatResponse(
                    answer=response.json().get("response", "Hello! How can I help you today?"),
                    response_id=response.json().get("job_id"),
                    confidence_score=0.85
                )
        
        # === PHASE 2: Execute Selected Tools ===
        logger.info(f"PHASE 2: Executing {len(selected_tools)} tools")
        
        # Build tool schemas for selected tools
        tool_schemas = []
        for tool_name in selected_tools:
            if tool_name in TOOL_REGISTRY and TOOL_REGISTRY[tool_name]["schema"]:
                tool_schemas.append(TOOL_REGISTRY[tool_name]["schema"])
        
        if not tool_schemas:
            return ChatResponse(answer="I couldn't find the information you're looking for.", response_id=None, confidence_score=0.0)
        
        # Get tool parameters with context
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
            timeout=30
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
        
        # Process allergy updates if any
        for result in tool_results:
            if result.get("tool") in ["update_allergy_add", "update_allergy_remove"]:
                try:
                    from services.customer_memory_service import CustomerMemoryService
                    
                    # Get or create profile
                    if not customer_profile:
                        customer_profile = CustomerMemoryService.get_or_create_profile(db, req.client_id, req.restaurant_id)
                    
                    action = result.get("action")
                    allergies_to_update = result.get("allergies", [])
                    
                    if action == "add":
                        # Add new allergies
                        current_allergies = list(getattr(customer_profile, 'allergies', []) or [])
                        for allergy in allergies_to_update:
                            if allergy not in current_allergies:
                                current_allergies.append(allergy)
                        customer_profile.allergies = current_allergies
                        logger.info(f"Added allergies: {allergies_to_update}")
                    
                    elif action == "remove":
                        # Remove allergies
                        current_allergies = list(getattr(customer_profile, 'allergies', []) or [])
                        for allergy in allergies_to_update:
                            if allergy in current_allergies:
                                current_allergies.remove(allergy)
                        customer_profile.allergies = current_allergies
                        logger.info(f"Removed allergies: {allergies_to_update}")
                    
                    db.add(customer_profile)
                    db.commit()
                    logger.info(f"Updated customer allergies - current: {customer_profile.allergies}")
                    
                except Exception as e:
                    logger.error(f"Error updating allergies via tool: {e}")
        
        # === PHASE 3: Generate Contextual Response ===
        logger.info("PHASE 3: Generating contextual response")
        
        final_prompt = build_final_prompt(
            req.message,
            tool_results,
            restaurant_name,
            customer_profile,
            context_type,
            context_data,
            chat_history
        )
        
        final_response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={"message": final_prompt, "max_tokens": 400},
            timeout=30
        )
        
        if final_response.status_code == 200:
            answer = final_response.json().get("response", "")
            
            # Always try to update customer profile with new info
            try:
                from services.customer_memory_service import CustomerMemoryService
                extracted = CustomerMemoryService.extract_customer_info(req.message, customer_profile)
                if extracted:
                    logger.info(f"Extracted customer info: {extracted}")
                    CustomerMemoryService.update_customer_profile(db, req.client_id, req.restaurant_id, extracted)
                    db.commit()  # Ensure changes are saved
            except Exception as e:
                logger.error(f"Error updating customer profile: {e}")
            
            return ChatResponse(
                answer=answer,
                response_id=final_response.json().get("job_id"),
                confidence_score=0.95
            )
        
        return ChatResponse(
            answer="I apologize for the inconvenience. Please try again.",
            response_id=None,
            confidence_score=0.0
        )
        
    except requests.exceptions.Timeout:
        logger.error("MIA backend timeout - falling back to simple response")
        return ChatResponse(
            answer="I'm here to help! Our system is a bit busy right now, but I can still assist you. What would you like to know about our menu?",
            response_id=None,
            confidence_score=0.7
        )
    except Exception as e:
        logger.error(f"Error in V5: {e}", exc_info=True)
        return ChatResponse(
            answer="I apologize for the technical difficulty. Please try again.",
            response_id=None,
            confidence_score=0.0
        )

# Wrapper
def mia_chat_service_internal_tools_v5(req: Any, db: Session) -> Any:
    return generate_response_internal_tools_v5(req, db)