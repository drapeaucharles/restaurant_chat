"""
Hybrid MIA Chat Service - Best of Both Worlds
Combines Maria personality prompts with simplified parameters for MIA compatibility
Includes Redis caching with graceful fallback
"""
import requests
import json
import re
from typing import Dict, Optional, List, Tuple
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from schemas.chat import ChatRequest, ChatResponse
from sqlalchemy.exc import IntegrityError
from services.restaurant_service import apply_menu_fallbacks
import os
import logging
from enum import Enum
from services.enhanced_response_cache import HybridCache

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

# Initialize cache (will use Redis if available, otherwise in-memory)
# Extract Redis connection details from environment
redis_url = os.getenv("REDIS_URL")
if redis_url:
    # Parse Redis URL to get host and port
    from urllib.parse import urlparse
    parsed = urlparse(redis_url)
    cache = HybridCache(
        redis_host=parsed.hostname or "localhost",
        redis_port=parsed.port or 6379,
        redis_db=0,
        ttl=3600
    )
else:
    # Use individual settings or defaults
    cache = HybridCache(
        redis_host=os.getenv("REDIS_HOST", "localhost"),
        redis_port=int(os.getenv("REDIS_PORT", "6379")),
        redis_db=int(os.getenv("REDIS_DB", "0")),
        ttl=3600
    )

class QueryType(Enum):
    GREETING = "greeting"
    MENU_QUERY = "menu_query"
    SPECIFIC_ITEM = "specific_item"
    RECOMMENDATION = "recommendation"
    HOURS = "hours"
    DIETARY = "dietary"
    OTHER = "other"

class HybridQueryClassifier:
    """Query classification for hybrid service"""
    
    @staticmethod
    def classify(query: str) -> QueryType:
        """Classify query into categories"""
        query_lower = query.lower().strip()
        
        # Check for greetings
        greeting_words = ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening', 
                         'bonjour', 'hola', 'ciao', 'salut', 'buenas', 'bom dia']
        if any(word in query_lower.split() for word in greeting_words):
            return QueryType.GREETING
        
        # Check for specific items
        food_items = ['pasta', 'pizza', 'dessert', 'wine', 'appetizer', 'salad', 'soup', 
                      'chicken', 'beef', 'fish', 'seafood', 'vegetarian', 'vegan']
        if any(item in query_lower for item in food_items):
            return QueryType.SPECIFIC_ITEM
        
        # Check for menu queries
        menu_words = ['menu', 'what do you have', 'what do you serve', 'options', 'dishes']
        if any(word in query_lower for word in menu_words):
            return QueryType.MENU_QUERY
        
        # Check for recommendations
        if 'recommend' in query_lower or 'suggest' in query_lower or 'best' in query_lower:
            return QueryType.RECOMMENDATION
        
        # Check for hours
        if 'hour' in query_lower or 'open' in query_lower or 'close' in query_lower:
            return QueryType.HOURS
        
        # Check for dietary
        dietary_words = ['vegetarian', 'vegan', 'gluten', 'allergy', 'dairy', 'nuts']
        if any(word in query_lower for word in dietary_words):
            return QueryType.DIETARY
        
        return QueryType.OTHER

def get_maria_system_prompt(restaurant_name: str, query_type: QueryType, language: str = "en") -> str:
    """Get Maria personality prompts based on query type and language"""
    
    # Maria's personality by language
    personalities = {
        "en": {
            "name": "Maria",
            "greeting": "warm and professional",
            "style": "friendly yet knowledgeable"
        },
        "es": {
            "name": "María",
            "greeting": "cálida y acogedora",
            "style": "amigable y servicial"
        },
        "fr": {
            "name": "Marie",
            "greeting": "chaleureuse et élégante",
            "style": "sophistiquée mais accessible"
        }
    }
    
    persona = personalities.get(language, personalities["en"])
    
    base_prompt = f"""You are {persona['name']}, a {persona['style']} restaurant assistant at {restaurant_name}.

Your personality:
- Be {persona['greeting']} while maintaining professionalism
- Show genuine enthusiasm about the menu
- Be helpful and attentive to customer needs
- Respond naturally in the customer's language

Important rules:
1. ONLY mention items that exist in the provided menu
2. Always include prices when listing dishes
3. Keep responses concise but friendly
4. If asked about items not on the menu, politely explain what similar options are available"""
    
    # Add query-specific guidance
    if query_type == QueryType.GREETING:
        base_prompt += f"""

For greetings: Welcome the customer warmly as {persona['name']}. Ask how you can help them today. 
Do NOT list menu items unless specifically asked."""
    
    elif query_type == QueryType.MENU_QUERY:
        base_prompt += """

For menu queries: Present the menu categories in an organized way. 
Mention that you can provide details about any specific category."""
    
    elif query_type == QueryType.SPECIFIC_ITEM:
        base_prompt += """

For specific items: List ALL items in that category with enthusiasm.
Briefly describe what makes each dish special."""
    
    elif query_type == QueryType.RECOMMENDATION:
        base_prompt += """

For recommendations: Suggest 2-3 dishes with personal touches.
Explain why you recommend each dish based on popular choices or unique features."""
    
    elif query_type == QueryType.DIETARY:
        base_prompt += """

For dietary needs: Show understanding and care for their requirements.
Clearly indicate which dishes meet their needs and suggest modifications if possible."""
    
    return base_prompt

def get_hybrid_parameters(query_type: QueryType) -> Dict:
    """Get generation parameters compatible with MIA"""
    
    # Use only parameters that MIA definitely supports
    if query_type == QueryType.GREETING:
        return {
            "temperature": 0.8,
            "max_tokens": 150
        }
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
    elif query_type == QueryType.DIETARY:
        return {
            "temperature": 0.4,
            "max_tokens": 350
        }
    else:
        return {
            "temperature": 0.7,
            "max_tokens": 200
        }

def detect_language(text: str) -> str:
    """Simple language detection based on common words"""
    spanish_words = ['hola', 'buenas', 'quiero', 'tiene', 'por favor', 'gracias']
    french_words = ['bonjour', 'bonsoir', 'je', 'voudrais', 'avez-vous', 'merci']
    
    text_lower = text.lower()
    spanish_count = sum(1 for word in spanish_words if word in text_lower)
    french_count = sum(1 for word in french_words if word in text_lower)
    
    if spanish_count > french_count and spanish_count > 0:
        return "es"
    elif french_count > 0:
        return "fr"
    else:
        return "en"

def build_hybrid_context(menu_items: List[Dict], query_type: QueryType, query: str) -> str:
    """Build context for Maria's responses"""
    
    if not menu_items:
        return "\nNo menu information available."
    
    context_parts = []
    
    if query_type == QueryType.GREETING:
        # Minimal context for greetings
        return ""
    
    elif query_type == QueryType.SPECIFIC_ITEM:
        # Find specific category items
        query_lower = query.lower()
        relevant_items = []
        
        # Check for specific food types
        if 'pasta' in query_lower:
            for item in menu_items:
                name = (item.get('dish') or item.get('name', '')).lower()
                desc = item.get('description', '').lower()
                subcategory = item.get('subcategory', '').lower()
                if 'pasta' in name or 'pasta' in desc or subcategory == 'pasta' or \
                   any(pasta in name for pasta in ['spaghetti', 'ravioli', 'penne', 'linguine', 'gnocchi', 'lasagna', 'fettuccine']):
                    relevant_items.append(item)
        
        elif 'pizza' in query_lower:
            for item in menu_items:
                name = (item.get('dish') or item.get('name', '')).lower()
                if 'pizza' in name:
                    relevant_items.append(item)
        
        elif 'dessert' in query_lower:
            for item in menu_items:
                if item.get('subcategory', '').lower() == 'dessert':
                    relevant_items.append(item)
        
        if relevant_items:
            context_parts.append(f"\nRelevant menu items for the customer's request:")
            for item in relevant_items:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                desc = item.get('description', '')
                if desc:
                    context_parts.append(f"- {name} ({price}): {desc}")
                else:
                    context_parts.append(f"- {name} ({price})")
    
    elif query_type == QueryType.MENU_QUERY:
        # Organized menu overview
        context_parts.append("\nOur menu categories:")
        categories = {}
        
        for item in menu_items:
            cat = item.get('subcategory', 'main dishes')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item)
        
        for cat, items in categories.items():
            context_parts.append(f"\n{cat.title()} ({len(items)} items):")
            # Show first 3 items as examples
            for item in items[:3]:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                context_parts.append(f"  - {name} ({price})")
            if len(items) > 3:
                context_parts.append(f"  ... and {len(items) - 3} more")
    
    elif query_type == QueryType.RECOMMENDATION:
        # Select some popular items
        context_parts.append("\nPopular dishes to consider:")
        # Pick diverse items
        recommendations = []
        categories_seen = set()
        
        for item in menu_items:
            cat = item.get('subcategory', 'main')
            if cat not in categories_seen and len(recommendations) < 5:
                recommendations.append(item)
                categories_seen.add(cat)
        
        for item in recommendations:
            name = item.get('dish') or item.get('name', '')
            price = item.get('price', '')
            desc = item.get('description', '')
            if desc:
                context_parts.append(f"- {name} ({price}): {desc}")
            else:
                context_parts.append(f"- {name} ({price})")
    
    return "\n".join(context_parts)

def get_mia_response_hybrid(prompt: str, params: Dict) -> str:
    """Get response from MIA with error handling"""
    try:
        request_data = {
            "prompt": prompt,
            "max_tokens": params.get("max_tokens", 200),
            "temperature": params.get("temperature", 0.7),
            "source": "restaurant-hybrid"
        }
        
        logger.info(f"Sending to MIA: {json.dumps(request_data)[:200]}...")
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-hybrid"
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
                return "I apologize, but I'm having trouble responding. Please try again."
        else:
            logger.error(f"MIA API error: {response.status_code}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again."
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "I apologize, but the response is taking too long. Please try again."
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}", exc_info=True)
        return "I apologize, but I'm having technical issues. Please try again or ask our staff."

def mia_chat_service_hybrid(req: ChatRequest, db: Session) -> ChatResponse:
    """Hybrid chat service with Maria personality and MIA compatibility"""
    
    logger.info(f"HYBRID SERVICE - Restaurant: {req.restaurant_id}, Message: '{req.message}'")
    
    # Skip AI for restaurant staff messages
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Classify query first
    query_type = HybridQueryClassifier.classify(req.message)
    logger.info(f"Query classified as: {query_type.value}")
    
    # Detect language
    language = detect_language(req.message)
    logger.info(f"Detected language: {language}")
    
    # Check cache
    cached_response = cache.get(req.message, req.restaurant_id, query_type.value)
    
    if cached_response:
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
    
    try:
        # Get restaurant data
        data = restaurant.data or {}
        restaurant_name = data.get('restaurant_name', req.restaurant_id)
        
        # Get menu items
        menu_items = data.get("menu", [])
        if menu_items:
            menu_items = apply_menu_fallbacks(menu_items)
        
        # Build Maria's prompt
        system_prompt = get_maria_system_prompt(restaurant_name, query_type, language)
        context = build_hybrid_context(menu_items, query_type, req.message)
        
        # Add hours if needed
        if query_type == QueryType.HOURS:
            hours = data.get('opening_hours', 'Hours not specified')
            context += f"\n\nOpening hours: {hours}"
        
        # Construct final prompt
        full_prompt = system_prompt
        if context:
            full_prompt += "\n" + context
        full_prompt += f"\n\nCustomer: {req.message}\n{get_persona_name(language)}:"
        
        logger.info(f"Prompt length: {len(full_prompt)} chars")
        
        # Get parameters
        params = get_hybrid_parameters(query_type)
        
        # Get AI response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Cache the response
        cache.set(req.message, req.restaurant_id, query_type.value, answer)
        
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
        logger.error(f"Error in hybrid service: {e}", exc_info=True)
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

def get_persona_name(language: str) -> str:
    """Get Maria's name in the appropriate language"""
    names = {
        "en": "Maria",
        "es": "María", 
        "fr": "Marie"
    }
    return names.get(language, "Maria")

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