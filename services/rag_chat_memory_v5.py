"""
Memory Working V5 - Adding Context Formatter
Testing if context formatter breaks the service
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.chat import ChatRequest, ChatResponse
from services.mia_chat_service_hybrid import (
    get_mia_response_hybrid, 
    detect_language,
    HybridQueryClassifier,
    QueryType,
    get_hybrid_parameters
)
from services.embedding_service import embedding_service
from services.response_validator import response_validator
from services.allergen_service import allergen_service
from services.context_formatter import context_formatter, ContextSection  # ADD THIS
from services.redis_helper import redis_client
import models
import re
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Global memory store as backup
MEMORY_STORE = {}

class WorkingMemoryRAGV5:
    """Working memory + Classification + Validation + Allergen + Context Formatter"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        
    def get_memory_key(self, restaurant_id: str, client_id: str) -> str:
        """Get memory key"""
        return f"memory_v5:{restaurant_id}:{client_id}"
    
    def get_memory(self, restaurant_id: str, client_id: str) -> Dict:
        """Get memory with fallback"""
        key = self.get_memory_key(restaurant_id, client_id)
        
        # Try Redis first
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
        
        # Fallback to local memory - EXPANDED structure
        return MEMORY_STORE.get(key, {
            'name': None,
            'history': [],
            'preferences': [],
            'dietary_restrictions': [],
            'mentioned_items': [],
            'topics': []
        })
    
    def save_memory(self, restaurant_id: str, client_id: str, memory: Dict):
        """Save memory with fallback"""
        key = self.get_memory_key(restaurant_id, client_id)
        
        # Save to local store first
        MEMORY_STORE[key] = memory
        
        # Try Redis
        try:
            redis_client.setex(key, 14400, json.dumps(memory))  # 4 hours
        except Exception as e:
            logger.warning(f"Redis save failed: {e}")
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat with all features"""
        
        # Get existing memory FIRST
        memory = self.get_memory(req.restaurant_id, req.client_id)
        logger.info(f"V5: Retrieved memory for {req.client_id}: name={memory.get('name')}, history={len(memory.get('history', []))}")
        
        # Extract name from current message
        name_match = re.search(r'my name is (\w+)', req.message, re.IGNORECASE)
        if name_match:
            memory['name'] = name_match.group(1).capitalize()
            logger.info(f"V5: Captured name: {memory['name']}")
        
        # Classify query type
        try:
            query_type = HybridQueryClassifier.classify(req.message)
            language = detect_language(req.message)
            logger.info(f"V5: Query type: {query_type.value}, Language: {language}")
        except Exception as e:
            logger.error(f"V5: Classification failed: {e}")
            query_type = QueryType.GENERAL
            language = "en"
        
        # Get restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="Restaurant not found.")
        
        restaurant_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
        
        # NEW: Initialize context sections
        context_sections = {}
        
        # Add restaurant info section
        context_sections[ContextSection.RESTAURANT_INFO] = f"Restaurant: {restaurant_name}"
        
        # Add personalization if we know the customer
        if memory.get('name'):
            context_sections[ContextSection.PERSONALIZATION] = f"Customer name: {memory['name']} (use their name in your response)"
        
        # Add conversation history
        if memory.get('history'):
            history_parts = ["Recent conversation:"]
            for item in memory['history'][-3:]:
                history_parts.append(f"Customer: {item['q']}")
                history_parts.append(f"You: {item['a'][:100]}...")
            context_sections[ContextSection.CONVERSATION_HISTORY] = "\n".join(history_parts)
        
        # Check for dietary mentions
        message_lower = req.message.lower()
        dietary_keywords = ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free', 'kosher', 'halal']
        for diet in dietary_keywords:
            if diet in message_lower and diet not in memory.get('dietary_restrictions', []):
                memory.setdefault('dietary_restrictions', []).append(diet)
                logger.info(f"V5: Added dietary restriction: {diet}")
        
        if memory.get('dietary_restrictions'):
            context_sections[ContextSection.DIETARY_INFO] = f"Customer dietary restrictions: {', '.join(memory['dietary_restrictions'])}"
        
        # Check if this is an allergen/dietary query
        is_allergen_query = any(word in message_lower for word in [
            'allerg', 'nut', 'dairy', 'gluten', 'shellfish'
        ] + memory.get('dietary_restrictions', []))
        
        # Get menu items
        if True and len(req.message) > 10:  # was query_type not in [QueryType.GREETING]
            try:
                if is_allergen_query:
                    # Use allergen service for dietary queries
                    logger.info(f"V5: Using allergen service for query")
                    allergen_data = allergen_service.get_items_for_restriction(
                        db, req.restaurant_id, message_lower
                    )
                    
                    menu_parts = []
                    if allergen_data['safe_items']:
                        menu_parts.append(f"Items suitable for {allergen_data['restriction_type']}:")
                        for item in allergen_data['safe_items'][:5]:
                            menu_parts.append(f"- {item['name']} (${item['price']}): {item['description'][:50]}...")
                    
                    if allergen_data['unsafe_items'] and len(allergen_data['unsafe_items']) < 10:
                        menu_parts.append(f"\nItems to AVOID (contain {allergen_data['allergen']}):")
                        for item in allergen_data['unsafe_items'][:3]:
                            menu_parts.append(f"- {item['name']}")
                    
                    if menu_parts:
                        context_sections[ContextSection.MENU_ITEMS] = "\n".join(menu_parts)
                else:
                    # Regular embedding search
                    items = self.embedding_service.search_similar_items(
                        db=db,
                        restaurant_id=req.restaurant_id,
                        query=req.message,
                        limit=5,
                        threshold=0.35
                    )
                    
                    if items:
                        menu_parts = ["Relevant menu items:"]
                        for item in items:
                            menu_parts.append(f"- {item['name']} (${item['price']})")
                        context_sections[ContextSection.MENU_ITEMS] = "\n".join(menu_parts)
            except Exception as e:
                logger.warning(f"V5: Menu search failed: {e}")
        
        # Add instructions
        instructions = [
            "Be friendly and helpful",
            "If you know the customer's name, use it naturally",
            "Keep responses concise",
            "Only mention items from the context"
        ]
        
        if memory.get('dietary_restrictions'):
            instructions.append(f"Be careful about their dietary restrictions: {', '.join(memory.get('dietary_restrictions'))}")
        
        context_sections[ContextSection.INSTRUCTIONS] = "\n".join(f"- {inst}" for inst in instructions)
        
        # NEW: Use context formatter to build the prompt
        context = context_formatter.format_context(
            sections=context_sections,
            query=req.message,
            language=language
        )
        
        # Handle specific queries about name
        if ('my name' in message_lower or 'remember' in message_lower) and memory.get('name'):
            prompt = f"""{context}

Customer asked: {req.message}

You should acknowledge that you know their name is {memory['name']} and use it in your response.
Be friendly and personal."""
        else:
            prompt = f"""{context}

Customer: {req.message}

Response:"""
        
        # Get AI response
        try:
            params = get_hybrid_parameters(query_type)
            logger.info(f"V5: Using params for {query_type.value}: {params}")
        except Exception as e:
            logger.error(f"V5: Failed to get params: {e}")
            params = {
                'max_tokens': 200,
                'temperature': 0.7
            }
        
        answer = get_mia_response_hybrid(prompt, params)
        
        # Validate response
        try:
            logger.info(f"V5: Validating response...")
            validated_answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
            if answer != validated_answer:
                logger.info(f"V5: Response was modified by validator")
            answer = validated_answer
        except Exception as e:
            logger.error(f"V5: Response validation failed: {e}")
        
        # Update history
        memory.setdefault('history', []).append({
            'q': req.message,
            'a': answer,
            'time': datetime.now().isoformat(),
            'query_type': query_type.value,
            'was_allergen_query': is_allergen_query
        })
        
        # Keep only last 10 exchanges
        memory['history'] = memory['history'][-10:]
        
        # Save memory for next time
        self.save_memory(req.restaurant_id, req.client_id, memory)
        logger.info(f"V5: Saved memory for {req.client_id}: name={memory.get('name')}, dietary={memory.get('dietary_restrictions', [])}")
        
        return ChatResponse(
            answer=answer,
            timestamp=req.message
        )

# Create singleton
working_memory_rag_v5 = WorkingMemoryRAGV5()