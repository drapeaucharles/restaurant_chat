"""
Memory Working V3 - Adding Response Validation
Testing if response validation breaks the service
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
from services.response_validator import response_validator  # ADD THIS
from services.redis_helper import redis_client
import models
import re
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Global memory store as backup
MEMORY_STORE = {}

class WorkingMemoryRAGV3:
    """Working memory + Query Classification + Response Validation"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        
    def get_memory_key(self, restaurant_id: str, client_id: str) -> str:
        """Get memory key"""
        return f"memory_v3:{restaurant_id}:{client_id}"
    
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
        
        # Fallback to local memory
        return MEMORY_STORE.get(key, {
            'name': None,
            'history': [],
            'preferences': []
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
        """Process chat with working memory + classification + validation"""
        
        # Get existing memory FIRST
        memory = self.get_memory(req.restaurant_id, req.client_id)
        logger.info(f"V3: Retrieved memory for {req.client_id}: name={memory.get('name')}, history={len(memory.get('history', []))}")
        
        # Extract name from current message
        name_match = re.search(r'my name is (\w+)', req.message, re.IGNORECASE)
        if name_match:
            memory['name'] = name_match.group(1).capitalize()
            logger.info(f"V3: Captured name: {memory['name']}")
        
        # Classify query type
        try:
            query_type = HybridQueryClassifier.classify(req.message)
            language = detect_language(req.message)
            logger.info(f"V3: Query type: {query_type.value}, Language: {language}")
        except Exception as e:
            logger.error(f"V3: Classification failed: {e}")
            query_type = QueryType.GENERAL
            language = "en"
        
        # Get restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="Restaurant not found.")
        
        restaurant_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
        
        # Build context with memory
        context_parts = [f"Restaurant: {restaurant_name}"]
        
        # Add customer info if known
        if memory.get('name'):
            context_parts.append(f"Customer name: {memory['name']} (use their name in your response)")
        
        # Add recent history
        if memory.get('history'):
            context_parts.append("\nRecent conversation:")
            for item in memory['history'][-3:]:
                context_parts.append(f"Customer: {item['q']}")
                context_parts.append(f"You: {item['a'][:100]}...")
        
        # Check for dietary mentions
        message_lower = req.message.lower()
        for diet in ['vegetarian', 'vegan', 'gluten-free']:
            if diet in message_lower and diet not in memory.get('preferences', []):
                memory.setdefault('preferences', []).append(diet)
        
        if memory.get('preferences'):
            context_parts.append(f"\nCustomer preferences: {', '.join(memory['preferences'])}")
        
        # Get relevant menu items if not just greeting
        if query_type not in [QueryType.GREETING] and len(req.message) > 10:
            try:
                items = self.embedding_service.search_similar_items(
                    db=db,
                    restaurant_id=req.restaurant_id,
                    query=req.message,
                    limit=5,
                    threshold=0.35
                )
                
                if items:
                    context_parts.append("\nRelevant menu items:")
                    for item in items:
                        context_parts.append(f"- {item['name']} (${item['price']})")
            except Exception as e:
                logger.warning(f"V3: Menu search failed: {e}")
        
        # Build prompt
        context = "\n".join(context_parts)
        
        # Handle specific queries about name
        if ('my name' in message_lower or 'remember' in message_lower) and memory.get('name'):
            prompt = f"""{context}

Customer asked: {req.message}

You should acknowledge that you know their name is {memory['name']} and use it in your response.
Be friendly and personal."""
        else:
            prompt = f"""{context}

Customer: {req.message}

Instructions:
- Be friendly and helpful
- If you know the customer's name, use it naturally
- Keep responses concise
- Only mention items from the context

Response:"""
        
        # Get AI response with query-type specific parameters
        try:
            params = get_hybrid_parameters(query_type)
            logger.info(f"V3: Using params for {query_type.value}: {params}")
        except Exception as e:
            logger.error(f"V3: Failed to get params: {e}")
            params = {
                'max_tokens': 200,
                'temperature': 0.7
            }
        
        answer = get_mia_response_hybrid(prompt, params)
        
        # NEW: Validate response
        try:
            logger.info(f"V3: Validating response...")
            validated_answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
            if answer != validated_answer:
                logger.info(f"V3: Response was modified by validator")
            answer = validated_answer
        except Exception as e:
            logger.error(f"V3: Response validation failed: {e}")
            # Keep original answer if validation fails
        
        # Update history
        memory.setdefault('history', []).append({
            'q': req.message,
            'a': answer,
            'time': datetime.now().isoformat(),
            'query_type': query_type.value
        })
        
        # Keep only last 10 exchanges
        memory['history'] = memory['history'][-10:]
        
        # Save memory for next time
        self.save_memory(req.restaurant_id, req.client_id, memory)
        logger.info(f"V3: Saved memory for {req.client_id}: name={memory.get('name')}")
        
        return ChatResponse(
            answer=answer,
            timestamp=req.message
        )

# Create singleton
working_memory_rag_v3 = WorkingMemoryRAGV3()