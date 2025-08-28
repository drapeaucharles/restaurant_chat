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
    get_mia_response_hybrid
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


def mia_chat_service_full_menu(req: ChatRequest, db: Session) -> ChatResponse:
    """Full menu chat service - sends complete menu in compact format"""
    
    try:
        logger.info(f"FULL MENU SERVICE - Request from client {req.client_id}: {req.message[:50]}...")
        
        # Skip AI for restaurant staff messages
        if req.sender_type == 'restaurant':
            logger.info("Blocking AI response for restaurant staff message")
            return ChatResponse(answer="")
        
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
        
        # Build system prompt with personality
        system_prompt = f"""You are Maria, a friendly server at {business_name}.

Be warm but concise:
- Sound natural, not robotic
- Keep responses short (2-4 sentences max)
- React genuinely but briefly ("Oh, you want steak!")
- Suggest 2-3 items with a quick reason why they're good
- Include prices naturally in conversation
- When customer asks for "X or similar", find X first, then suggest related items

Example for "or similar" requests:
Customer: "I want steak or things similar"
You: "Oh, you want something hearty! Our Ribeye ($38.99) is amazing, and we also have the Grilled Lamb Chops ($35.99) or our Beef Medallions ($32.99) if you want other red meats. What sounds good?"

Menu items below show [ingredients] and {allergens}."""
        
        # Build compact menu context
        menu_context = build_compact_menu_context(menu_items, business_type)
        
        # For full menu mode, we don't need complex query analysis
        query_lower = req.message.lower()
        
        # Build full prompt
        full_prompt = f"""{system_prompt}

{menu_context}

Customer: {req.message}
Assistant:"""
        
        logger.info(f"Full menu prompt length: {len(full_prompt)} chars (~{len(full_prompt)//4} tokens)")
        
        # Check for "or similar" pattern and enhance prompt
        if 'or similar' in query_lower or 'or things similar' in query_lower or 'like' in query_lower:
            # Extract the main item being requested
            main_item = None
            if 'steak' in query_lower:
                main_item = 'steak'
            elif 'chicken' in query_lower:
                main_item = 'chicken'
            elif 'fish' in query_lower:
                main_item = 'fish'
            
            if main_item:
                full_prompt = full_prompt.replace("Assistant:", f"""
Remember: Customer is asking for {main_item} OR similar items. First mention {main_item} options, then suggest related dishes.
Assistant:""")
        
        # DEBUG: Log items with specific ingredients
        if 'steak' in query_lower:
            steak_items = []
            meat_items = []
            for item in menu_items:
                name = (item.get('dish') or item.get('name', '')).lower()
                ingredients = [str(ing).lower() for ing in item.get('ingredients', [])]
                
                if 'steak' in name or 'ribeye' in name or 'sirloin' in name:
                    steak_items.append(f"{item.get('dish', item.get('name', ''))} - {item.get('price', '')}")
                elif any(meat in name or any(meat in ing for ing in ingredients) for meat in ['beef', 'lamb', 'pork', 'veal']):
                    meat_items.append(f"{item.get('dish', item.get('name', ''))} - {item.get('price', '')}")
                    
            logger.info(f"Steak items found: {len(steak_items)}")
            for item in steak_items[:3]:
                logger.info(f"  {item}")
            logger.info(f"Other meat items found: {len(meat_items)}")
            for item in meat_items[:3]:
                logger.info(f"  {item}")
        
        # Get AI response with simple parameters
        params = {
            "temperature": 0.7,
            "max_tokens": 300
        }
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
        
    except Exception as e:
        logger.error(f"Error in full_menu service: {str(e)}", exc_info=True)
        # Try to rollback database if needed
        try:
            db.rollback()
        except:
            pass
        
        # Return a more helpful error message
        if "timeout" in str(e).lower():
            return ChatResponse(answer="The AI service is taking longer than expected. Please try again.")
        elif "connection" in str(e).lower():
            return ChatResponse(answer="I'm having trouble connecting to our AI service. Please try again in a moment.")
        else:
            return ChatResponse(answer="I apologize, but I'm having technical difficulties. Please try again or ask our staff for assistance.")