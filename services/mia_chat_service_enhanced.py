"""
Enhanced MIA Chat Service with immediate improvements:
- Enhanced system prompts with role-playing
- Redis-based response caching
- Dynamic temperature adjustment
- Query type detection
"""
import requests
import redis
import json
import re
from hashlib import md5
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from schemas.chat import ChatRequest, ChatResponse
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from services.restaurant_service import apply_menu_fallbacks
import os
import logging
from typing import Dict, Optional, List
from enum import Enum

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_LOCAL_URL = os.getenv("MIA_LOCAL_URL", "http://localhost:8000")

# Redis configuration
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

class QueryType(Enum):
    GREETING = "greeting"
    MENU_QUERY = "menu_query"
    SPECIFIC_ITEM = "specific_item"
    RECOMMENDATION = "recommendation"
    HOURS = "hours"
    CONTACT = "contact"
    DIETARY = "dietary"
    OTHER = "other"

class ResponseCache:
    """Redis-based response cache for common queries"""
    
    def __init__(self):
        try:
            self.redis_client = redis.Redis(
                host=REDIS_HOST, 
                port=REDIS_PORT, 
                db=REDIS_DB,
                decode_responses=True
            )
            self.redis_client.ping()  # Test connection
            self.enabled = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis not available, caching disabled: {e}")
            self.enabled = False
            self.redis_client = None
        
        self.ttl = 3600  # 1 hour cache for most queries
        self.greeting_ttl = 86400  # 24 hours for greetings
    
    def get_cache_key(self, query: str, restaurant_id: str, language: str = "en") -> str:
        """Generate cache key from query"""
        normalized = query.lower().strip()
        key_data = f"{restaurant_id}:{language}:{normalized}"
        return f"chat:{md5(key_data.encode()).hexdigest()}"
    
    def get(self, query: str, restaurant_id: str, language: str = "en") -> Optional[str]:
        """Get cached response if available"""
        if not self.enabled:
            return None
            
        try:
            key = self.get_cache_key(query, restaurant_id, language)
            cached = self.redis_client.get(key)
            if cached:
                logger.info(f"Cache hit for query: {query[:50]}...")
                return json.loads(cached)["response"]
            return None
        except Exception as e:
            logger.error(f"Cache get error: {e}")
            return None
    
    def set(self, query: str, restaurant_id: str, response: str, query_type: QueryType, language: str = "en"):
        """Cache response with appropriate TTL"""
        if not self.enabled:
            return
            
        try:
            key = self.get_cache_key(query, restaurant_id, language)
            ttl = self.greeting_ttl if query_type == QueryType.GREETING else self.ttl
            
            data = {
                "response": response,
                "query_type": query_type.value,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            self.redis_client.setex(key, ttl, json.dumps(data))
            logger.info(f"Cached response for query: {query[:50]}...")
        except Exception as e:
            logger.error(f"Cache set error: {e}")

class QueryAnalyzer:
    """Analyze queries to determine type and extract key information"""
    
    def __init__(self):
        # Keywords for different query types
        self.greeting_patterns = [
            r'^(hi|hello|hey|good\s+(morning|afternoon|evening)|greetings?)',
            r'^(bonjour|bonsoir|salut)',  # French
            r'^(hola|buenos\s+d[ií]as|buenas\s+tardes)',  # Spanish
            r'^(ciao|buongiorno|buonasera)',  # Italian
        ]
        
        self.menu_patterns = [
            r'(menu|what\s+do\s+you\s+(have|serve|offer))',
            r'(show|list|tell)\s+me\s+.*menu',
            r'what.*\s+(food|dishes?|options?)',
            r'qu\'?est[- ]ce\s+que\s+vous\s+avez',  # French
            r'que\s+tienen',  # Spanish
        ]
        
        self.specific_patterns = [
            r'(tell|what|info).*about\s+(?:the\s+)?(.+)',
            r'(describe|explain).*\s+(.+)',
            r'(price|cost|how\s+much).*\s+(.+)',
        ]
        
        self.recommendation_patterns = [
            r'(recommend|suggest|what\s+should\s+i)',
            r'(best|popular|favorite|special)',
            r'what\s+do\s+you\s+recommend',
            r'que\s+me\s+recomienda',  # Spanish
            r'que\s+recommandez[- ]vous',  # French
        ]
        
        self.hours_patterns = [
            r'(hours?|open|close|when)',
            r'(horaire|heure)',  # French
            r'(horario|abierto|cerrado)',  # Spanish
        ]
        
        self.dietary_patterns = [
            r'(vegetarian|vegan|gluten[- ]free|dairy[- ]free|allergen)',
            r'(dietary|restriction|allergy)',
            r'(végétarien|végétalien|sans\s+gluten)',  # French
            r'(vegetariano|vegano|sin\s+gluten)',  # Spanish
        ]
    
    def detect_language(self, text: str) -> str:
        """Detect the primary language of input text"""
        text_lower = text.lower()
        
        # Spanish indicators
        spanish_chars = set('ñáéíóúü¿¡')
        spanish_words = {'hola', 'cómo', 'está', 'qué', 'gracias', 'por', 'favor', 'quiero', 'tiene'}
        
        # French indicators
        french_chars = set('àâçèéêëîïôùûüÿœæ')
        french_words = {'bonjour', 'comment', 'allez', 'vous', 'merci', 'sil', 'plait', 'avoir'}
        
        # Italian indicators
        italian_words = {'ciao', 'buongiorno', 'grazie', 'prego', 'cosa', 'avete', 'vorrei'}
        
        if any(c in text_lower for c in spanish_chars) or any(w in text_lower.split() for w in spanish_words):
            return 'es'
        elif any(c in text_lower for c in french_chars) or any(w in text_lower.split() for w in french_words):
            return 'fr'
        elif any(w in text_lower.split() for w in italian_words):
            return 'it'
        else:
            return 'en'
    
    def analyze(self, query: str) -> Dict:
        """Analyze query and return type, language, and other metadata"""
        query_lower = query.lower().strip()
        
        # Detect language
        language = self.detect_language(query)
        
        # Check each pattern type
        for pattern in self.greeting_patterns:
            if re.search(pattern, query_lower):
                return {
                    "type": QueryType.GREETING,
                    "language": language,
                    "keywords": []
                }
        
        for pattern in self.menu_patterns:
            if re.search(pattern, query_lower):
                # Check if asking about specific category
                categories = ['pasta', 'pizza', 'salad', 'dessert', 'starter', 'main', 'beverage', 'wine']
                found_categories = [cat for cat in categories if cat in query_lower]
                
                return {
                    "type": QueryType.MENU_QUERY,
                    "language": language,
                    "categories": found_categories,
                    "keywords": query_lower.split()
                }
        
        for pattern in self.dietary_patterns:
            if re.search(pattern, query_lower):
                return {
                    "type": QueryType.DIETARY,
                    "language": language,
                    "keywords": re.findall(r'(vegetarian|vegan|gluten[- ]free|dairy[- ]free)', query_lower)
                }
        
        for pattern in self.recommendation_patterns:
            if re.search(pattern, query_lower):
                return {
                    "type": QueryType.RECOMMENDATION,
                    "language": language,
                    "keywords": []
                }
        
        for pattern in self.hours_patterns:
            if re.search(pattern, query_lower):
                return {
                    "type": QueryType.HOURS,
                    "language": language,
                    "keywords": []
                }
        
        # Check for specific item queries
        for pattern in self.specific_patterns:
            match = re.search(pattern, query_lower)
            if match:
                item_name = match.group(2) if match.lastindex >= 2 else match.group(1)
                return {
                    "type": QueryType.SPECIFIC_ITEM,
                    "language": language,
                    "item": item_name.strip(),
                    "keywords": [item_name.strip()]
                }
        
        # Default to OTHER
        return {
            "type": QueryType.OTHER,
            "language": language,
            "keywords": [w for w in query_lower.split() if len(w) > 2]
        }

def get_enhanced_system_prompt(restaurant_name: str, query_analysis: Dict) -> str:
    """Generate enhanced system prompt based on query type and language"""
    
    language = query_analysis.get("language", "en")
    query_type = query_analysis.get("type", QueryType.OTHER)
    
    # Base personality in different languages
    personalities = {
        "en": f"""You are Maria, a professional and friendly restaurant assistant at {restaurant_name}.

Your personality:
- Warm and welcoming, but professional
- Knowledgeable about every dish on our menu
- Enthusiastic about making recommendations
- Attentive to dietary needs and preferences

Important rules:
1. ONLY mention items that are actually on the provided menu - never invent dishes
2. Include prices when listing menu items
3. Be concise but informative
4. Match the customer's language and tone""",
        
        "es": f"""Eres María, una asistente profesional y amigable del restaurante {restaurant_name}.

Tu personalidad:
- Cálida y acogedora, pero profesional
- Conocedora de cada plato en nuestro menú
- Entusiasta al hacer recomendaciones
- Atenta a las necesidades dietéticas

Reglas importantes:
1. SOLO menciona platos que están en el menú proporcionado
2. Incluye precios al listar platos
3. Sé concisa pero informativa
4. Responde en el idioma del cliente""",
        
        "fr": f"""Vous êtes Marie, une assistante professionnelle et sympathique du restaurant {restaurant_name}.

Votre personnalité:
- Chaleureuse et accueillante, mais professionnelle
- Connaît parfaitement chaque plat du menu
- Enthousiaste pour faire des recommandations
- Attentive aux besoins alimentaires

Règles importantes:
1. Mentionnez UNIQUEMENT les plats du menu fourni
2. Incluez les prix
3. Soyez concise mais informative
4. Répondez dans la langue du client"""
    }
    
    base_prompt = personalities.get(language, personalities["en"])
    
    # Add query-specific guidance
    if query_type == QueryType.GREETING:
        base_prompt += "\n\nFor greetings: Respond warmly and ask how you can help. Don't list menu items unless asked."
    elif query_type == QueryType.MENU_QUERY:
        base_prompt += "\n\nFor menu queries: Organize items by category. Include name, price, and a brief description."
    elif query_type == QueryType.RECOMMENDATION:
        base_prompt += "\n\nFor recommendations: Suggest 2-3 items with enthusiastic descriptions and reasons why they're special."
    elif query_type == QueryType.DIETARY:
        base_prompt += "\n\nFor dietary queries: Carefully list ONLY items that meet the dietary requirement. Be clear about ingredients."
    
    return base_prompt

def get_dynamic_parameters(query_type: QueryType) -> Dict:
    """Get optimized generation parameters based on query type"""
    
    params = {
        QueryType.GREETING: {
            "temperature": 0.8,
            "top_p": 0.95,
            "frequency_penalty": 0.5,
            "presence_penalty": 0.3,
            "max_tokens": 100
        },
        QueryType.MENU_QUERY: {
            "temperature": 0.3,
            "top_p": 0.85,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.1,
            "max_tokens": 400
        },
        QueryType.SPECIFIC_ITEM: {
            "temperature": 0.4,
            "top_p": 0.85,
            "frequency_penalty": 0.2,
            "presence_penalty": 0.1,
            "max_tokens": 200
        },
        QueryType.RECOMMENDATION: {
            "temperature": 0.6,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.3,
            "max_tokens": 300
        },
        QueryType.DIETARY: {
            "temperature": 0.3,
            "top_p": 0.85,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
            "max_tokens": 350
        },
        QueryType.HOURS: {
            "temperature": 0.2,
            "top_p": 0.8,
            "frequency_penalty": 0.1,
            "presence_penalty": 0.1,
            "max_tokens": 100
        },
        QueryType.OTHER: {
            "temperature": 0.7,
            "top_p": 0.9,
            "frequency_penalty": 0.3,
            "presence_penalty": 0.2,
            "max_tokens": 200
        }
    }
    
    return params.get(query_type, params[QueryType.OTHER])

def get_mia_response_enhanced(prompt: str, params: Dict) -> str:
    """Get response from MIA with dynamic parameters"""
    try:
        # Skip local MIA if configured
        skip_local = os.getenv("SKIP_LOCAL_MIA", "true").lower() == "true"
        
        request_data = {
            "prompt": prompt,
            "max_tokens": params.get("max_tokens", 200),
            "temperature": params.get("temperature", 0.7),
            "top_p": params.get("top_p", 0.9),
            "frequency_penalty": params.get("frequency_penalty", 0.3),
            "presence_penalty": params.get("presence_penalty", 0.3),
            "source": "restaurant-enhanced"
        }
        
        # Try remote MIA backend
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-enhanced"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", result.get("response", ""))
            if text:
                return text.strip()
            else:
                logger.warning("MIA returned empty response")
                return "I'm having trouble understanding. Could you please rephrase?"
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            return "I apologize, but I'm having technical difficulties. Please try again in a moment."
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "I'm taking a bit longer to respond. Please try again."
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}")
        return "I'm experiencing technical difficulties. Please try again or ask our staff for help."

def build_context_for_query(menu_items: List[Dict], query_analysis: Dict, restaurant_data: Dict) -> str:
    """Build optimized context based on query type"""
    
    query_type = query_analysis["type"]
    context_parts = []
    
    if query_type == QueryType.GREETING:
        # Minimal context for greetings
        context_parts.append(f"Restaurant hours: {restaurant_data.get('opening_hours', 'Not specified')}")
        
    elif query_type == QueryType.MENU_QUERY:
        # Organize menu by categories
        categories = query_analysis.get("categories", [])
        
        if categories:
            # Filter to specific categories
            filtered_items = []
            for item in menu_items:
                item_category = item.get('subcategory', '').lower()
                if any(cat in item_category for cat in categories):
                    filtered_items.append(item)
            
            if filtered_items:
                context_parts.append(f"\nMenu items ({', '.join(categories)}):")
                for item in filtered_items[:15]:  # Limit items
                    name = item.get('dish') or item.get('name', '')
                    price = item.get('price', '')
                    desc = item.get('description', '')[:100]
                    context_parts.append(f"- {name} ({price}): {desc}")
        else:
            # General menu overview
            menu_by_category = {}
            for item in menu_items:
                category = item.get('subcategory', 'main')
                if category not in menu_by_category:
                    menu_by_category[category] = []
                menu_by_category[category].append(item)
            
            context_parts.append("\nMenu Overview:")
            for category, items in menu_by_category.items():
                sample_items = [item.get('dish') or item.get('name', '') for item in items[:3]]
                context_parts.append(f"{category.title()} ({len(items)} items): {', '.join(sample_items)}...")
    
    elif query_type == QueryType.SPECIFIC_ITEM:
        # Find specific item
        item_name = query_analysis.get("item", "").lower()
        found_items = []
        
        for item in menu_items:
            name = (item.get('dish') or item.get('name', '')).lower()
            if item_name in name or name in item_name:
                found_items.append(item)
        
        if found_items:
            context_parts.append("\nRelevant items:")
            for item in found_items[:5]:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                desc = item.get('description', '')
                ingredients = ', '.join(item.get('ingredients', []))
                context_parts.append(f"{name} ({price}): {desc}")
                if ingredients:
                    context_parts.append(f"  Ingredients: {ingredients}")
    
    elif query_type == QueryType.DIETARY:
        # Filter by dietary requirements
        keywords = query_analysis.get("keywords", [])
        filtered_items = []
        
        for item in menu_items:
            tags = item.get('dietary_tags', [])
            desc = (item.get('description', '') + ' '.join(item.get('ingredients', []))).lower()
            
            if any(keyword in desc or keyword in tags for keyword in keywords):
                filtered_items.append(item)
        
        if filtered_items:
            context_parts.append(f"\nDietary options ({', '.join(keywords)}):")
            for item in filtered_items[:10]:
                name = item.get('dish') or item.get('name', '')
                price = item.get('price', '')
                context_parts.append(f"- {name} ({price})")
    
    elif query_type == QueryType.RECOMMENDATION:
        # Get popular/special items
        special_items = [item for item in menu_items if 'special' in item.get('description', '').lower() or 
                        'popular' in item.get('description', '').lower() or
                        'signature' in item.get('description', '').lower()]
        
        if not special_items:
            # Get random selection from different categories
            categories = {}
            for item in menu_items:
                cat = item.get('subcategory', 'main')
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            special_items = []
            for cat, items in categories.items():
                if items:
                    special_items.append(items[0])
        
        context_parts.append("\nOur specialties:")
        for item in special_items[:5]:
            name = item.get('dish') or item.get('name', '')
            price = item.get('price', '')
            desc = item.get('description', '')
            context_parts.append(f"- {name} ({price}): {desc}")
    
    elif query_type == QueryType.HOURS:
        hours = restaurant_data.get('opening_hours', {})
        context_parts.append(f"\nOpening hours: {hours}")
        context_parts.append(f"Contact: {restaurant_data.get('contact_info', 'Not specified')}")
    
    return "\n".join(context_parts)

# Initialize global instances
cache = ResponseCache()
analyzer = QueryAnalyzer()

def mia_chat_service_enhanced(req: ChatRequest, db: Session) -> ChatResponse:
    """Enhanced chat service with caching, dynamic parameters, and better prompts"""
    
    logger.info(f"ENHANCED MIA SERVICE - Restaurant: {req.restaurant_id}, Client: {req.client_id}")
    logger.info(f"Query: '{req.message}'")
    
    # Skip AI for restaurant staff messages
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Analyze query
    query_analysis = analyzer.analyze(req.message)
    logger.info(f"Query analysis: Type={query_analysis['type'].value}, Language={query_analysis['language']}")
    
    # Check cache first
    cached_response = cache.get(req.message, req.restaurant_id, query_analysis['language'])
    if cached_response:
        logger.info("Returning cached response")
        # Save to database even for cached responses
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=cached_response
        )
        db.add(new_message)
        db.commit()
        return ChatResponse(answer=cached_response)
    
    # Get restaurant data
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        logger.error(f"Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    data = restaurant.data or {}
    
    try:
        # Get menu items
        menu_items = data.get("menu", [])
        if menu_items:
            try:
                menu_items = apply_menu_fallbacks(menu_items)
            except Exception as e:
                logger.warning(f"Error applying menu fallbacks: {e}")
        
        # Build enhanced system prompt
        restaurant_name = data.get('restaurant_name', req.restaurant_id)
        system_prompt = get_enhanced_system_prompt(restaurant_name, query_analysis)
        
        # Build optimized context
        context = build_context_for_query(menu_items, query_analysis, data)
        
        # Get recent conversation history (last 3 exchanges)
        recent_messages = fetch_recent_chat_history(db, req.client_id, req.restaurant_id, limit=6)
        conversation_context = ""
        if len(recent_messages) > 1:
            conversation_context = "\nRecent conversation:\n"
            for msg in recent_messages[:-1]:  # Exclude current message
                role = "Customer" if msg.sender_type == "client" else "You"
                conversation_context += f"{role}: {msg.message}\n"
        
        # Construct final prompt
        full_prompt = system_prompt
        if context:
            full_prompt += "\n" + context
        if conversation_context:
            full_prompt += "\n" + conversation_context
        full_prompt += f"\n\nCustomer: {req.message}\nYou:"
        
        # Get dynamic parameters
        params = get_dynamic_parameters(query_analysis['type'])
        
        # Get AI response
        answer = get_mia_response_enhanced(full_prompt, params)
        
        # Cache the response
        cache.set(req.message, req.restaurant_id, answer, query_analysis['type'], query_analysis['language'])
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        logger.info("Enhanced response generated successfully")
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in enhanced MIA chat service: {e}")
        return ChatResponse(answer="I'm experiencing technical difficulties. Please try again later.")

def fetch_recent_chat_history(db: Session, client_id: str, restaurant_id: str, limit: int = 20):
    """Fetch recent chat history for context"""
    cutoff_time = datetime.utcnow() - timedelta(minutes=60)
    
    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == client_id,
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.timestamp >= cutoff_time,
        models.ChatMessage.sender_type.in_(['client', 'ai'])
    ).order_by(models.ChatMessage.timestamp.asc()).limit(limit).all()
    
    return recent_messages

def get_or_create_client(db: Session, client_id: str, restaurant_id: str, phone_number: str = None):
    """Get or create a client record."""
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
    else:
        if phone_number and not client.phone_number:
            client.phone_number = phone_number
            db.commit()
            db.refresh(client)
    return client