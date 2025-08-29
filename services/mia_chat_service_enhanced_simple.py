"""
Enhanced MIA Chat Service - Simplified Version
Keeps core improvements but removes advanced parameters that might cause issues
"""
import requests
import json
import re
from typing import Dict, Optional, List
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from schemas.chat import ChatRequest, ChatResponse
from sqlalchemy.exc import IntegrityError
from services.restaurant_service import apply_menu_fallbacks
import os
import logging
from enum import Enum

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

class QueryType(Enum):
    MENU_QUERY = "menu_query"
    SPECIFIC_ITEM = "specific_item"
    RECOMMENDATION = "recommendation"
    HOURS = "hours"
    DIETARY = "dietary"
    OTHER = "other"

class SimpleQueryClassifier:
    """Simplified query classification"""
    
    @staticmethod
    def classify(query: str) -> QueryType:
        """Classify query into categories"""
        query_lower = query.lower().strip()
        
        # Check for greetings
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 
                         'bonjour', 'hola', 'ciao', 'salut']
        if any(word in query_lower.split() for word in greeting_words):
            return QueryType.OTHER  # was QueryType.GREETING
        
        # Check for menu queries
        if 'pasta' in query_lower or 'pizza' in query_lower or 'dessert' in query_lower:
            return QueryType.SPECIFIC_ITEM
        elif 'menu' in query_lower or 'what do you have' in query_lower or 'what do you serve' in query_lower:
            return QueryType.MENU_QUERY
        
        # Check for recommendations
        if 'recommend' in query_lower or 'suggest' in query_lower or 'best' in query_lower:
            return QueryType.RECOMMENDATION
        
        # Check for hours
        if 'hour' in query_lower or 'open' in query_lower or 'close' in query_lower:
            return QueryType.HOURS
        
        # Check for dietary
        if 'vegetarian' in query_lower or 'vegan' in query_lower or 'gluten' in query_lower:
            return QueryType.DIETARY
        
        return QueryType.OTHER

def get_simple_system_prompt(restaurant_name: str, query_type: QueryType) -> str:
    """Get simplified system prompt based on query type"""
    
    base_prompt = f"""You are a friendly assistant for {restaurant_name}.

Important rules:
1. ONLY mention items from the provided menu
2. Include prices when listing items
3. Be helpful and concise
4. Respond in the customer's language"""
    
    # Add query-specific guidance
    # Removed GREETING special case - let AI handle naturally

    if False:  # was query_type == QueryType.GREETING

        pass
    elif query_type == QueryType.MENU_QUERY:
        base_prompt += "\n\nFor menu queries: List items clearly with names and prices."
    elif query_type == QueryType.SPECIFIC_ITEM:
        base_prompt += "\n\nFor specific items: List ALL items in that category with prices."
    elif query_type == QueryType.RECOMMENDATION:
        base_prompt += "\n\nFor recommendations: Suggest 2-3 items with brief descriptions."
    
    return base_prompt

def get_simple_parameters(query_type: QueryType) -> Dict:
    """Get simplified generation parameters"""
    
    # Use only basic parameters that MIA definitely supports
    # Removed GREETING special case - let AI handle naturally

    if False:  # was query_type == QueryType.GREETING

        pass
    elif query_type in [QueryType.MENU_QUERY, QueryType.SPECIFIC_ITEM]:
        return {
            "temperature": 0.3,
            "max_tokens": 400
        }
    elif query_type == QueryType.RECOMMENDATION:
        return {
            "temperature": 0.6,
            "max_tokens": 300
        }
    else:
        return {
            "temperature": 0.7,
            "max_tokens": 200
        }

def get_mia_response_simple(prompt: str, params: Dict) -> str:
    """Get response from MIA with simple parameters"""
    try:
        # Use only basic parameters that MIA supports
        request_data = {
            "prompt": prompt,
            "max_tokens": params.get("max_tokens", 200),
            "temperature": params.get("temperature", 0.7),
            "source": "restaurant-enhanced-simple"
        }
        
        logger.info(f"Sending to MIA: {json.dumps(request_data)[:200]}...")
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-enhanced"
            },
            timeout=30
        )
        
        logger.info(f"MIA response status: {response.status_code}")
        logger.info(f"MIA response headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            result = response.json()
            logger.info(f"MIA response data: {json.dumps(result)[:500]}")
            
            # Try different response fields
            text = result.get("text") or result.get("response") or result.get("answer") or ""
            
            if text:
                logger.info(f"Got response text: {text[:100]}...")
                return text.strip()
            else:
                logger.warning(f"MIA returned empty text. Full response: {json.dumps(result)}")
                # Return debug info if empty
                return f"Debug: MIA returned empty text. Response keys: {list(result.keys())}"
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            return f"MIA Error {response.status_code}: {response.text[:200]}"
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "Error: MIA request timed out after 30 seconds"
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}", exc_info=True)
        return f"Error: {type(e).__name__}: {str(e)}"

def build_simple_context(menu_items: List[Dict], query_type: QueryType, query: str) -> str:
    """Build simplified context based on query type"""
    
    if not menu_items:
        return "\nNo menu information available."
    
    context_parts = []
    
    # Removed GREETING special case - let AI handle naturally

    
    if False:  # was query_type == QueryType.GREETING

    
        pass
    
    elif query_type == QueryType.SPECIFIC_ITEM:
        # Find specific category items
        query_lower = query.lower()
        relevant_items = []
        
        if 'pasta' in query_lower:
            for item in menu_items:
                name = (item.get('dish') or item.get('name', '')).lower()
                desc = item.get('description', '').lower()
                if 'pasta' in name or 'pasta' in desc or any(pasta in name for pasta in ['spaghetti', 'ravioli', 'penne', 'linguine', 'gnocchi', 'lasagna']):
                    relevant_items.append(item)
        
        if relevant_items:
            context_parts.append(f"\nMenu items (please list ALL of these):")
            for item in relevant_items:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                context_parts.append(f"- {name} ({price})")
    
    elif query_type == QueryType.MENU_QUERY:
        # General menu overview
        context_parts.append("\nMenu overview:")
        # Group by category
        categories = {}
        for item in menu_items[:30]:  # Limit to avoid context overflow
            cat = item.get('subcategory', 'main')
            if cat not in categories:
                categories[cat] = []
            name = item.get('dish') or item.get('name', '')
            if name:
                categories[cat].append(name)
        
        for cat, items in categories.items():
            context_parts.append(f"{cat}: {len(items)} items")
    
    return "\n".join(context_parts)

# Simple in-memory cache
_simple_cache = {}

def mia_chat_service_enhanced_simple(req: ChatRequest, db: Session) -> ChatResponse:
    """Simplified enhanced chat service"""
    
    logger.info(f"ENHANCED SIMPLE - Restaurant: {req.restaurant_id}, Message: '{req.message}'")
    
    # Skip AI for restaurant staff messages
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Check simple cache
    cache_key = f"{req.restaurant_id}:{req.message.lower().strip()}"
    if cache_key in _simple_cache:
        cached_time, cached_response = _simple_cache[cache_key]
        if (datetime.now() - cached_time).seconds < 3600:  # 1 hour cache
            logger.info("Returning cached response")
            # Save to DB
            new_message = models.ChatMessage(
                restaurant_id=req.restaurant_id,
                client_id=req.client_id,
                sender_type="ai",
                message=cached_response
            )
            db.add(new_message)
            db.commit()
            return ChatResponse(answer=cached_response)
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        logger.error(f"Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    # Classify query
    query_type = SimpleQueryClassifier.classify(req.message)
    logger.info(f"Query classified as: {query_type.value}")
    
    try:
        # Get restaurant data
        data = restaurant.data or {}
        restaurant_name = data.get('restaurant_name', req.restaurant_id)
        
        # Get menu items
        menu_items = data.get("menu", [])
        if menu_items:
            menu_items = apply_menu_fallbacks(menu_items)
        
        # Build simple prompt
        system_prompt = get_simple_system_prompt(restaurant_name, query_type)
        context = build_simple_context(menu_items, query_type, req.message)
        
        # Add hours if needed
        if query_type == QueryType.HOURS:
            hours = data.get('opening_hours', 'Hours not specified')
            context += f"\n\nOpening hours: {hours}"
        
        # Construct final prompt
        full_prompt = system_prompt
        if context:
            full_prompt += "\n" + context
        full_prompt += f"\n\nCustomer: {req.message}\nAssistant:"
        
        logger.info(f"Prompt length: {len(full_prompt)} chars")
        
        # Get simple parameters
        params = get_simple_parameters(query_type)
        
        # Get AI response
        answer = get_mia_response_simple(full_prompt, params)
        
        # Cache the response
        _simple_cache[cache_key] = (datetime.now(), answer)
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        logger.info(f"Response generated: {answer[:100]}...")
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in enhanced simple service: {e}", exc_info=True)
        # Return a fallback response
        fallback = "I apologize, but I'm having technical difficulties. Please try again or ask our staff for assistance."
        
        # Still save the error response
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=fallback
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(answer=fallback)

def get_or_create_client(db: Session, client_id: str, restaurant_id: str, phone_number: str = None):
    """Get or create a client record"""
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        try:
            client = models.Client(
                id=client_id, 
                restaurant_id=restaurant_id,
                phone_number=phone_number
            )
            db.add(client)
            db.commit()
            db.refresh(client)
        except IntegrityError:
            db.rollback()
            client = db.query(models.Client).filter_by(id=client_id).first()
    return client