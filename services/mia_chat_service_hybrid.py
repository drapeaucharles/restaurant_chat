"""
Hybrid MIA Chat Service - Best of Both Worlds
Combines Maria personality prompts with simplified parameters for MIA compatibility
Includes Redis caching with graceful fallback
"""
import requests
import json
import re
import time
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
try:
    from services.negation_detector import NegationDetector
except ImportError:
    NegationDetector = None

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
        
        # Check for specific items or ingredients
        food_items = ['pasta', 'pizza', 'dessert', 'wine', 'appetizer', 'salad', 'soup', 
                      'chicken', 'beef', 'fish', 'seafood', 'vegetarian', 'vegan', 
                      'eggs', 'egg', 'cheese', 'mushroom', 'tomato', 'sauce']
        ingredient_phrases = ['love', 'want', 'with', 'contain', 'include', 'have']
        
        # Check if query mentions food items or is asking about ingredients
        if any(item in query_lower for item in food_items):
            return QueryType.SPECIFIC_ITEM
        if any(phrase in query_lower for phrase in ingredient_phrases) and len(query_lower.split()) < 10:
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
    """
    Natural language detection based on the query language
    Let the AI respond in the same language as the user
    """
    text_lower = text.lower()
    
    # Count language indicators
    spanish_indicators = ['qué', 'cómo', 'dónde', 'cuánto', 'tiene', 'hay', 'quiero', 'puedo', 'platos', 'comida']
    french_indicators = ['qu\'est', 'comment', 'où', 'combien', 'avez', 'je', 'puis', 'plats', 'nourriture']
    portuguese_indicators = ['o que', 'como', 'onde', 'quanto', 'tem', 'há', 'quero', 'posso', 'pratos', 'comida']
    
    # Count matches for each language
    spanish_score = sum(1 for word in spanish_indicators if word in text_lower)
    french_score = sum(1 for word in french_indicators if word in text_lower)
    portuguese_score = sum(1 for word in portuguese_indicators if word in text_lower)
    
    # Return the language with highest score, default to English if no clear match
    if spanish_score > max(french_score, portuguese_score) and spanish_score >= 2:
        return "es"
    elif french_score > max(spanish_score, portuguese_score) and french_score >= 2:
        return "fr"
    elif portuguese_score > max(spanish_score, french_score) and portuguese_score >= 2:
        return "pt"
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
        
        # Check for negation patterns using advanced detector
        if NegationDetector:
            is_negative, negated_items = NegationDetector.detect_negation(query_lower)
            preferences = NegationDetector.extract_preferences(query_lower)
        else:
            # Fallback to simple detection
            negation_words = ["don't", "dont", "do not", "no ", "without", "avoid", "dislike", "hate", "allergic"]
            is_negative = any(neg in query_lower for neg in negation_words)
            negated_items = []
            preferences = {'likes': [], 'dislikes': []}
        
        # Check for ingredient requests
        ingredient_triggers = ['contain', 'with', 'have', 'include', 'love', 'like', 'want', 'need', 'prefer', 'enjoy']
        if any(word in query_lower for word in ingredient_triggers + negation_words):
            logger.info(f"Hybrid: Processing ingredient request for query: {query_lower}")
            # Look for specific ingredients mentioned
            for item in menu_items:
                item_ingredients = item.get('ingredients', [])
                item_allergens = item.get('allergens', [])
                item_desc = item.get('description', '').lower()
                
                # Check if any word in query matches ingredients
                should_include = False
                for word in query_lower.split():
                    if len(word) > 3:  # Skip short words
                        has_ingredient = (any(word in ing.lower() for ing in item_ingredients) or
                                        any(word in allerg.lower() for allerg in item_allergens) or
                                        word in item_desc)
                        
                        if is_negative and has_ingredient:
                            # Exclude items with this ingredient
                            should_include = False
                            break
                        elif not is_negative and has_ingredient:
                            # Include items with this ingredient
                            should_include = True
                            break
                
                # For negative queries, include items that DON'T have the ingredient
                if is_negative and not should_include:
                    # Check if item doesn't contain any of the unwanted ingredients
                    unwanted_found = False
                    
                    # Use detected negated items if available
                    items_to_check = negated_items if negated_items else [w for w in query_lower.split() if len(w) > 3 and w not in negation_words]
                    
                    for unwanted_item in items_to_check:
                        if (any(unwanted_item in ing.lower() for ing in item_ingredients) or
                            any(unwanted_item in allerg.lower() for allerg in item_allergens)):
                            unwanted_found = True
                            break
                    
                    if not unwanted_found:
                        relevant_items.append(item)
                elif not is_negative and should_include:
                    relevant_items.append(item)
            
            # DEBUG log results
            logger.info(f"Hybrid: Found {len(relevant_items)} relevant items for ingredient search")
        
        # Check for specific food types
        elif 'pasta' in query_lower:
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
            # Check if this is an ingredient-specific query
            is_ingredient_query = any(word in query_lower for word in ['contain', 'with', 'have', 'include', 'love', 'want'] + negation_words)
            
            if is_negative:
                context_parts.append(f"\nMenu items WITHOUT the ingredients you want to avoid:")
            elif is_ingredient_query:
                context_parts.append(f"\nMenu items that match your request:")
            else:
                context_parts.append(f"\nRelevant menu items for the customer's request:")
            
            for item in relevant_items:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                desc = item.get('description', '')
                ingredients = item.get('ingredients', [])
                
                # For ingredient queries, show ingredients clearly
                if is_ingredient_query and ingredients:
                    context_parts.append(f"- {name} ({price}): {desc}")
                    context_parts.append(f"  Ingredients: {', '.join(ingredients)}")
                elif desc:
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
            "message": prompt,  # Changed from "prompt" to "message"
            "max_tokens": params.get("max_tokens", 200),
            "temperature": params.get("temperature", 0.7)
        }
        
        logger.info(f"Sending to MIA: {json.dumps(request_data)[:200]}...")
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",  # Changed from /api/generate to /chat
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-hybrid"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if it's a job response
            job_id = result.get("job_id")
            if job_id:
                logger.info(f"Job queued with ID: {job_id}, polling for result...")
                
                # Poll for result
                max_polls = 30  # 30 seconds max
                for i in range(max_polls):
                    time.sleep(1)
                    
                    poll_response = requests.get(
                        f"{MIA_BACKEND_URL}/job/{job_id}/result",
                        timeout=5
                    )
                    
                    if poll_response.status_code == 200:
                        poll_result = poll_response.json()
                        
                        # Check if result is ready
                        if poll_result.get("result"):
                            # Handle different response formats
                            result_data = poll_result["result"]
                            if isinstance(result_data, str):
                                text = result_data
                            elif isinstance(result_data, dict):
                                text = result_data.get("text") or result_data.get("response") or result_data.get("output", "")
                            else:
                                text = str(result_data)
                            
                            if text:
                                logger.info(f"Got response from MIA: {text[:100]}...")
                                return text.strip()
                        elif poll_result.get("status") == "pending":
                            logger.debug(f"Job {job_id} still pending... ({i+1}/{max_polls})")
                            continue
                    elif poll_response.status_code == 404:
                        logger.debug(f"Job {job_id} not found yet... ({i+1}/{max_polls})")
                        continue
                
                logger.error(f"Job {job_id} timed out after {max_polls} seconds")
                return "I apologize, but the response is taking too long. Please try again."
            
            # Fallback to direct response if available
            text = result.get("text") or result.get("response") or result.get("answer") or ""
            if text:
                logger.info(f"Got direct response from MIA: {text[:100]}...")
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
    
    # Check cache (but skip for ingredient queries to ensure fresh results)
    skip_cache = any(word in req.message.lower() for word in ['egg', 'ingredient', 'contain', 'allerg'])
    
    # TEMPORARY: Force skip cache for debugging
    skip_cache = True  # TODO: Remove after cache is cleared
    
    cached_response = None if skip_cache else cache.get(req.message, req.restaurant_id, query_type.value)
    
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
        
        # DEBUG: Log menu data
        logger.info(f"Restaurant {restaurant.restaurant_id} has {len(menu_items)} menu items")
        if menu_items:
            # Count items with eggs
            egg_count = 0
            for item in menu_items:
                if any('egg' in str(ing).lower() for ing in item.get('ingredients', [])):
                    egg_count += 1
            logger.info(f"Items with eggs in ingredients: {egg_count}")
        
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
        logger.info(f"FULL PROMPT BEING SENT TO AI:\n{full_prompt[:1000]}...")
        
        # Get parameters
        params = get_hybrid_parameters(query_type)
        
        # Get AI response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Cache the response (but not if it's a "no items found" type response)
        negative_responses = ["don't have any", "no dishes", "don't offer", "not available", "sorry"]
        if not any(neg in answer.lower() for neg in negative_responses) or skip_cache:
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