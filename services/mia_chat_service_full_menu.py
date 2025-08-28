"""
Full Menu MIA Chat Service - Always sends complete menu in compact format
No complex search, no missing items, just all the data
"""
import requests
import json
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime
import models
from schemas.chat import ChatRequest, ChatResponse
import os
import logging
from services.mia_chat_service_hybrid import (
    get_mia_response_hybrid,
    detect_language,
    HybridQueryClassifier,
    QueryType,
    get_hybrid_parameters
)

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def build_compact_menu_context(menu_items: List[Dict], business_type: str = 'restaurant') -> str:
    """Build compact menu context with name, price, ingredients, allergens only"""
    
    if not menu_items:
        return "\nNo menu information available."
    
    context_parts = []
    
    if business_type == 'restaurant':
        context_parts.append("Our complete menu:")
        
        # Group by category
        categories = {}
        for item in menu_items:
            cat = item.get('category') or item.get('subcategory', 'Other')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        # Build compact listing
        for category, items in categories.items():
            context_parts.append(f"\n{category}:")
            for item in items:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                ingredients = item.get('ingredients', [])
                allergens = item.get('allergens', [])
                
                # Format: Name ($price) [ingredients] {allergens}
                line = f"• {name} ({price})"
                
                if ingredients:
                    ing_str = ', '.join(ingredients[:5])  # First 5 ingredients
                    if len(ingredients) > 5:
                        ing_str += f', +{len(ingredients)-5} more'
                    line += f" [{ing_str}]"
                
                if allergens:
                    line += f" {{{', '.join(allergens)}}}"
                
                context_parts.append(line)
                
    elif business_type == 'legal' or business_type == 'visa_consulting':
        context_parts.append("Our services:")
        
        # For legal businesses, group by service type
        service_types = {}
        for item in menu_items:
            service_type = item.get('category', 'General Services')
            if service_type not in service_types:
                service_types[service_type] = []
            service_types[service_type].append(item)
        
        for service_type, services in service_types.items():
            context_parts.append(f"\n{service_type}:")
            for service in services:
                name = service.get('name', '')
                price = service.get('price', '')
                duration = service.get('duration', '')
                requirements = service.get('requirements', [])
                
                line = f"• {name} ({price})"
                if duration:
                    line += f" - {duration}"
                if requirements and len(requirements) > 0:
                    line += f" [Requires: {', '.join(requirements[:3])}]"
                
                context_parts.append(line)
    
    else:
        # Generic business format
        context_parts.append("Our services/products:")
        for item in menu_items:
            name = item.get('name', '')
            price = item.get('price', '')
            context_parts.append(f"• {name} ({price})")
    
    return "\n".join(context_parts)

def get_description_if_needed(menu_items: List[Dict], item_names: List[str]) -> str:
    """Get descriptions for specific items when AI needs more detail"""
    descriptions = []
    
    for item_name in item_names:
        for item in menu_items:
            if (item.get('name', '').lower() == item_name.lower() or 
                item.get('dish', '').lower() == item_name.lower()):
                desc = item.get('description', '')
                if desc:
                    descriptions.append(f"{item_name}: {desc}")
                break
    
    if descriptions:
        return "\n\nDetailed descriptions:\n" + "\n".join(descriptions)
    return ""

def mia_chat_service_full_menu(req: ChatRequest, db: Session) -> ChatResponse:
    """Full menu chat service - sends complete menu in compact format"""
    
    logger.info(f"FULL MENU SERVICE - Request from client {req.client_id}")
    
    # Skip AI for restaurant staff messages
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Classify query
    query_type = HybridQueryClassifier.classify(req.message)
    logger.info(f"Query classified as: {query_type.value}")
    
    # Detect language
    language = detect_language(req.message)
    
    # Check if it's businesses or restaurants table
    from sqlalchemy import text
    
    # First try businesses table
    business_query = text("""
        SELECT business_type, data
        FROM businesses 
        WHERE business_id = :business_id
    """)
    business_result = db.execute(business_query, {"business_id": req.restaurant_id}).fetchone()
    
    if business_result:
        business_type, data = business_result
        business_name = data.get('name', req.restaurant_id) if data else req.restaurant_id
        menu_items = data.get('menu', []) if data else []
    else:
        # Fallback to restaurants table
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="I'm sorry, I cannot find information about this business.")
        
        business_type = 'restaurant'
        data = restaurant.data or {}
        business_name = data.get('restaurant_name', req.restaurant_id)
        menu_items = data.get('menu', [])
    
    # Build system prompt
    system_prompt = f"""You are a helpful assistant for {business_name}.
You have access to our complete menu/service list.
Be friendly and professional.
Always include prices when mentioning items.
If customers ask about descriptions, provide them.
For ingredients or allergen questions, use the information in brackets."""
    
    # Build compact menu context
    menu_context = build_compact_menu_context(menu_items, business_type)
    
    # Check if query mentions specific items that might need descriptions
    mentioned_items = []
    query_lower = req.message.lower()
    for item in menu_items[:20]:  # Check first 20 for efficiency
        item_name = (item.get('name') or item.get('dish', '')).lower()
        if item_name and len(item_name) > 3 and item_name in query_lower:
            mentioned_items.append(item.get('name') or item.get('dish'))
    
    # Get descriptions if specific items mentioned
    description_context = ""
    if mentioned_items and query_type == QueryType.SPECIFIC_ITEM:
        description_context = get_description_if_needed(menu_items, mentioned_items)
    
    # Build full prompt
    full_prompt = f"""{system_prompt}

{menu_context}
{description_context}

Customer: {req.message}
Assistant:"""
    
    logger.info(f"Full menu prompt length: {len(full_prompt)} chars (~{len(full_prompt)//4} tokens)")
    
    # Get AI response
    params = get_hybrid_parameters(query_type)
    answer = get_mia_response_hybrid(full_prompt, params)
    
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