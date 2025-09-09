"""
MIA Chat Service with Internal Tool Flow V5 - DEBUG VERSION
- Includes comprehensive debug logging
- Returns full flow information when debug=True
"""
import os
import requests
import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

# Copy all the imports and functions from V5
from .mia_chat_service_internal_tools_v5 import (
    create_menu_summary,
    TOOL_REGISTRY,
    get_context_type,
    build_phase1_prompt,
    execute_tool_from_registry,
    get_customer_profile,
    get_chat_history,
    build_final_prompt
)

MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def generate_response_internal_tools_v5_debug(req: Any, db: Session) -> Any:
    """V5 with comprehensive debug logging"""
    from schemas.chat import ChatResponse
    
    # Initialize debug collector
    debug_info = {
        "request": {
            "message": req.message,
            "restaurant_id": req.restaurant_id,
            "client_id": str(req.client_id)
        },
        "phase1": {},
        "phase2": {},
        "phase3": {},
        "flow_type": None,
        "errors": []
    }
    
    try:
        # Get restaurant data
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
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
            restaurant_data = json.loads(restaurant.data) if isinstance(restaurant.data, str) else restaurant.data
        
        # Extract menu items and restaurant name
        menu_items = restaurant_data.get('menu', [])
        restaurant_name = restaurant_data.get('business_name', 'our restaurant')
        
        debug_info["restaurant"] = {
            "name": restaurant_name,
            "menu_items_count": len(menu_items)
        }
        
        # Load customer profile
        customer_profile = get_customer_profile(db, req.client_id, req.restaurant_id)
        debug_info["customer"] = {
            "has_profile": customer_profile is not None,
            "allergies": getattr(customer_profile, 'allergies', []) if customer_profile else [],
            "dietary": getattr(customer_profile, 'dietary_restrictions', []) if customer_profile else []
        }
        
        # Load chat history
        chat_history = get_chat_history(db, req.client_id, req.restaurant_id, limit=3)
        debug_info["history_count"] = len(chat_history)
        
        # Determine context type
        context_type, context_data = get_context_type(customer_profile, req.message)
        debug_info["context"] = {
            "type": context_type,
            "data": context_data
        }
        
        # === PHASE 1: Tool Selection ===
        phase1_prompt = build_phase1_prompt(req.message, customer_profile, chat_history)
        debug_info["phase1"]["prompt"] = phase1_prompt
        debug_info["phase1"]["prompt_length"] = len(phase1_prompt)
        
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
            debug_info["errors"].append(f"Phase 1 failed: {response.status_code}")
            return ChatResponse(answer="I'm having trouble understanding. Please try again.", response_id=None, confidence_score=0.0)
        
        # Parse tool selection
        selection_text = response.json().get("response", "").strip()
        debug_info["phase1"]["raw_response"] = selection_text
        
        try:
            if "[" in selection_text and "]" in selection_text:
                start = selection_text.find("[")
                end = selection_text.rfind("]") + 1
                selected_tools = json.loads(selection_text[start:end])
            else:
                selected_tools = ["no_tool_needed"]
        except:
            selected_tools = ["no_tool_needed"]
        
        debug_info["phase1"]["selected_tools"] = selected_tools
        
        # Auto-add allergy tools if needed
        if context_type == "allergen_safety" and context_data.get('allergens'):
            original_tools = selected_tools.copy()
            allergen_tools_map = {
                'nuts': 'filter_nut_free',
                'dairy': 'filter_dairy_free',
                'gluten': 'filter_gluten_free'
            }
            
            for allergen in context_data['allergens']:
                tool_name = allergen_tools_map.get(allergen.lower())
                if tool_name and tool_name not in selected_tools:
                    selected_tools.append(tool_name)
            
            if selected_tools != original_tools:
                debug_info["phase1"]["auto_added_tools"] = list(set(selected_tools) - set(original_tools))
        
        # === SIMPLE FLOW ===
        if selected_tools == ["no_tool_needed"]:
            debug_info["flow_type"] = "simple"
            
            # Create menu summary
            menu_summary = create_menu_summary(menu_items)
            debug_info["simple_flow"] = {
                "menu_summary_length": len(menu_summary),
                "menu_summary_preview": menu_summary[:300] + "..."
            }
            
            # Build simple prompt with all context
            simple_prompt = f"""You are Maria at {restaurant_name}.

"""
            # Add restaurant context
            if restaurant_data:
                simple_prompt += f"""RESTAURANT INFO:
- Name: {restaurant_name}
- Hours: See website for hours

"""
            
            # Add customer profile
            if customer_profile:
                simple_prompt += "CUSTOMER PROFILE:\n"
                if getattr(customer_profile, 'name', None):
                    simple_prompt += f"- Name: {getattr(customer_profile, 'name')}\n"
                if getattr(customer_profile, 'allergies', []):
                    simple_prompt += f"- Allergies: {', '.join(getattr(customer_profile, 'allergies'))}\n"
                simple_prompt += "\n"
            
            # Add context warnings
            if context_type == "allergen_safety":
                simple_prompt += f"⚠️ CRITICAL: Customer has restrictions ({', '.join(context_data.get('all_restrictions', []))})\n\n"
            
            # Add chat history
            if chat_history and len(chat_history) > 1:
                simple_prompt += "CONVERSATION HISTORY:\n"
                for msg in chat_history[:-1]:
                    role = "Customer" if msg["role"] == "user" else "You"
                    simple_prompt += f"{role}: {msg['message']}\n"
                simple_prompt += "\n"
            
            # Add menu
            simple_prompt += f"""MENU INFORMATION:
{menu_summary}

Current Message:
Customer: "{req.message}"

RESPONSE GUIDELINES:
- Be CONCISE - max 2-3 sentences
- Answer their specific question directly
- USE ACTUAL MENU PRICES AND ITEMS from above
- NEVER make up dishes or prices"""
            
            debug_info["simple_flow"]["prompt_length"] = len(simple_prompt)
            debug_info["simple_flow"]["prompt_preview"] = simple_prompt[:500] + "..."
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={"message": simple_prompt, "max_tokens": 200},
                timeout=30
            )
            
            if response.status_code == 200:
                answer = response.json().get("response", "Hello! How can I help you today?")
                
                if getattr(req, 'debug', False):
                    return {
                        "answer": answer,
                        "debug": debug_info
                    }
                
                return ChatResponse(
                    answer=answer,
                    response_id=response.json().get("job_id"),
                    confidence_score=0.85
                )
        
        # === PHASE 2: Tool Execution ===
        debug_info["flow_type"] = "tools"
        debug_info["phase2"]["selected_tools"] = selected_tools
        
        # Build tool schemas
        tool_schemas = []
        for tool_name in selected_tools:
            if tool_name in TOOL_REGISTRY and TOOL_REGISTRY[tool_name]["schema"]:
                tool_schemas.append(TOOL_REGISTRY[tool_name]["schema"])
        
        if not tool_schemas:
            debug_info["errors"].append("No valid tool schemas found")
            return ChatResponse(answer="I couldn't find the information you're looking for.", response_id=None, confidence_score=0.0)
        
        # Get parameters for tools
        param_prompt = f"""Based on this request: "{req.message}"

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
            debug_info["errors"].append(f"Phase 2 param failed: {param_response.status_code}")
            return ChatResponse(answer="I'm having trouble processing your request.", response_id=None, confidence_score=0.0)
        
        # Execute tools
        tool_results = []
        param_data = param_response.json()
        debug_info["phase2"]["tool_calls"] = []
        
        if param_data.get("tool_calls"):
            for tool_call in param_data["tool_calls"]:
                if "function" in tool_call:
                    func_name = tool_call["function"]["name"]
                    args = json.loads(tool_call["function"].get("arguments", "{}"))
                    
                    # Find and execute tool
                    for reg_name, reg_info in TOOL_REGISTRY.items():
                        if reg_info["schema"] and reg_info["schema"]["function"]["name"] == func_name:
                            result = execute_tool_from_registry(reg_name, args, menu_items)
                            tool_results.append(result)
                            
                            debug_info["phase2"]["tool_calls"].append({
                                "tool": reg_name,
                                "function": func_name,
                                "arguments": args,
                                "result": result
                            })
                            break
        
        debug_info["phase2"]["tool_results_count"] = len(tool_results)
        
        # === PHASE 3: Final Response ===
        debug_info["phase3"]["has_tool_results"] = len(tool_results) > 0
        
        final_prompt = build_final_prompt(
            req.message,
            tool_results,
            restaurant_name,
            customer_profile,
            context_type,
            context_data,
            chat_history
        )
        
        debug_info["phase3"]["prompt_length"] = len(final_prompt)
        debug_info["phase3"]["prompt_preview"] = final_prompt[:500] + "..."
        
        final_response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={"message": final_prompt, "max_tokens": 400},
            timeout=30
        )
        
        if final_response.status_code == 200:
            answer = final_response.json().get("response", "")
            
            if getattr(req, 'debug', False):
                return {
                    "answer": answer,
                    "debug": debug_info
                }
            
            return ChatResponse(
                answer=answer,
                response_id=final_response.json().get("job_id"),
                confidence_score=0.95
            )
        
        debug_info["errors"].append(f"Phase 3 failed: {final_response.status_code}")
        return ChatResponse(
            answer="I apologize for the inconvenience. Please try again.",
            response_id=None,
            confidence_score=0.0
        )
        
    except Exception as e:
        debug_info["errors"].append(f"Exception: {str(e)}")
        
        if getattr(req, 'debug', False):
            return {
                "answer": "An error occurred",
                "debug": debug_info
            }
        
        return ChatResponse(
            answer="I apologize for the technical difficulty. Please try again.",
            response_id=None,
            confidence_score=0.0
        )

# Wrapper for compatibility
def mia_chat_service_internal_tools_v5_debug(req: Any, db: Session) -> Any:
    return generate_response_internal_tools_v5_debug(req, db)