"""
Simplified Full Menu MIA Chat Service
Since we send the complete menu, the AI can handle all queries without complex classification
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

def get_mia_response(prompt: str, max_tokens: int = 300) -> str:
    """Get response from MIA with simple error handling"""
    try:
        request_data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.7,
            "source": "restaurant-full-menu"
        }
        
        logger.info(f"Sending to MIA: {len(prompt)} chars")
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-full-menu"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("text") or result.get("response") or result.get("answer") or ""
            
            if text:
                logger.info(f"Got response from MIA: {text[:100]}...")
                return text.strip()
            else:
                logger.warning("MIA returned empty text")
                return "I'm having trouble processing that. Could you try again?"
        else:
            logger.error(f"MIA returned status code: {response.status_code}")
            return "I'm having technical difficulties. Please try again."
            
    except requests.Timeout:
        logger.error("MIA request timed out")
        return "The AI service is taking longer than expected. Please try again."
    except Exception as e:
        logger.error(f"Error calling MIA: {str(e)}", exc_info=True)
        return "I'm having trouble connecting to our AI service. Please try again in a moment."

def mia_chat_service_full_menu_simple(req: ChatRequest, db: Session) -> ChatResponse:
    """Simplified full menu chat service - AI handles everything with complete menu"""
    
    try:
        logger.info(f"FULL MENU SERVICE - Request from client {req.client_id}: {req.message[:50]}...")
        
        # Skip AI for restaurant staff messages
        if req.sender_type == 'restaurant':
            logger.info("Blocking AI response for restaurant staff message")
            return ChatResponse(answer="")
    
        # Get business data
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
        system_prompt = f"""You are Maria, a friendly server at {business_name}.

Be warm but concise:
- Sound natural and conversational
- Keep responses short (2-4 sentences max)
- React genuinely to customer requests
- Suggest 2-3 relevant items with prices
- Handle any type of query naturally

You have access to our complete menu below. Answer any question about our offerings, make recommendations, handle dietary restrictions, and chat naturally with customers.

Menu items show: Name (price) [ingredients] {{allergens}}"""
        
        # Build compact menu context
        menu_context = build_compact_menu_context(menu_items, business_type)
        
        # Build full prompt
        full_prompt = f"""{system_prompt}

{menu_context}

Customer: {req.message}
Assistant:"""
        
        logger.info(f"Prompt length: {len(full_prompt)} chars (~{len(full_prompt)//4} tokens)")
        
        # Get AI response
        answer = get_mia_response(full_prompt)
        
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
        try:
            db.rollback()
        except:
            pass
        
        return ChatResponse(answer="I apologize, but I'm having technical difficulties. Please try again or ask our staff for assistance.")