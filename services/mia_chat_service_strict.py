"""
Strict version of MIA chat service that enforces menu accuracy
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.mia_chat_service_hybrid import (
    HybridCache,
    QueryType,
    HybridQueryClassifier,
    detect_language,
    get_persona_name,
    get_mia_response_hybrid,
    get_hybrid_parameters
)
from schemas.chat import ChatRequest, ChatResponse
import models
import json

logger = logging.getLogger(__name__)

def get_strict_system_prompt(restaurant_name: str, query_type: QueryType, language: str, menu_items: List[Dict]) -> str:
    """Get VERY strict system prompt that includes actual menu items"""
    
    # Build menu item list
    menu_text = "ACTUAL MENU ITEMS (ONLY mention these):\n"
    for item in menu_items:
        name = item.get('dish') or item.get('name', '')
        price = item.get('price', '')
        desc = item.get('description', '')
        category = item.get('subcategory', '')
        
        menu_text += f"- {name} ({price})"
        if category:
            menu_text += f" [Category: {category}]"
        if desc:
            menu_text += f" - {desc}"
        menu_text += "\n"
    
    # Language-specific personas
    personas = {
        "en": {"name": "Maria", "style": "professional and friendly"},
        "es": {"name": "María", "style": "cálida y acogedora"},
        "fr": {"name": "Marie", "style": "chaleureuse et élégante"}
    }
    
    persona = personas.get(language, personas["en"])
    
    prompt = f"""You are {persona['name']}, assistant at {restaurant_name}.

CRITICAL RULES:
1. ONLY mention items from the ACTUAL MENU below
2. NEVER make up dishes, prices, or ingredients
3. All prices are in USD ($), NOT euros
4. If asked about something not on the menu, say "We don't have that, but we do have..." and suggest similar items
5. Be accurate with prices and descriptions

{menu_text}

REMEMBER: You can ONLY talk about the items listed above. Do not invent any other dishes."""
    
    # Add query-specific instructions
    if query_type == QueryType.SPECIFIC_ITEM:
        prompt += "\n\nList the relevant items from the menu above with their exact prices."
    elif query_type == QueryType.DIETARY:
        prompt += "\n\nCheck the menu carefully for dietary information. Only mention items that actually meet their requirements."
    
    return prompt

def mia_chat_service_strict(req: ChatRequest, db: Session) -> ChatResponse:
    """Strict version that enforces menu accuracy"""
    
    logger.info(f"STRICT SERVICE - Restaurant: {req.restaurant_id}, Message: '{req.message}'")
    
    # Skip AI for restaurant staff
    if req.sender_type == 'restaurant':
        return ChatResponse(answer="")
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    try:
        # Get restaurant data
        data = restaurant.data or {}
        restaurant_name = data.get('restaurant_name', req.restaurant_id)
        menu_items = data.get("menu", [])
        
        # Classify query
        query_type = HybridQueryClassifier.classify(req.message)
        language = detect_language(req.message)
        
        # Build STRICT prompt with actual menu
        system_prompt = get_strict_system_prompt(restaurant_name, query_type, language, menu_items)
        
        # Add the user query
        full_prompt = system_prompt + f"\n\nCustomer: {req.message}\n{get_persona_name(language)}:"
        
        logger.info(f"Strict prompt includes {len(menu_items)} menu items")
        
        # Get parameters
        params = get_hybrid_parameters(query_type)
        params["temperature"] = min(params.get("temperature", 0.7), 0.5)  # Lower temperature for accuracy
        
        # Get response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Verify response doesn't contain hallucinations
        answer_lower = answer.lower()
        if "€" in answer or "euro" in answer_lower:
            logger.warning("Response contains euros, correcting...")
            answer = answer.replace("€", "$").replace("euros", "dollars").replace("euro", "dollar")
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in strict service: {e}", exc_info=True)
        return ChatResponse(answer="I apologize, but I'm having trouble accessing the menu. Please try again.")

# Create singleton instance
mia_chat_service_strict_instance = mia_chat_service_strict