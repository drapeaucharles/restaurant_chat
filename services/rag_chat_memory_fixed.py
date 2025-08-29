"""
Fixed memory service with proper error handling
Based on memory_best but with exception handling to find issues
"""
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.chat import ChatRequest, ChatResponse
from services.mia_chat_service_hybrid import (
    HybridQueryClassifier,
    QueryType,
    get_hybrid_parameters,
    get_mia_response_hybrid,
    detect_language,
    get_persona_name
)
from services.embedding_service import embedding_service
from services.allergen_service import allergen_service
from services.context_formatter import context_formatter, ContextSection
from services.redis_helper import redis_client
import models
import re
import json
from datetime import datetime
import traceback

logger = logging.getLogger(__name__)

# Global memory store as backup
MEMORY_STORE = {}

class FixedMemoryRAG:
    """Fixed version with comprehensive error handling"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
        
    def get_memory_key(self, restaurant_id: str, client_id: str) -> str:
        """Get memory key"""
        return f"fixed_memory:{restaurant_id}:{client_id}"
    
    def get_memory(self, restaurant_id: str, client_id: str) -> Dict:
        """Get memory with all features"""
        key = self.get_memory_key(restaurant_id, client_id)
        
        # Try Redis first
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
        
        # Fallback to local memory with full structure
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
            logger.info(f"Memory saved to Redis: {key}")
        except Exception as e:
            logger.warning(f"Redis save failed: {e}")
    
    def extract_and_update_memory(self, memory: Dict, message: str, response: str):
        """Extract information from current exchange and update memory"""
        try:
            message_lower = message.lower()
            
            # Extract name
            name_match = re.search(r'my name is (\w+)', message, re.IGNORECASE)
            if name_match:
                memory['name'] = name_match.group(1).capitalize()
                logger.info(f"Captured name: {memory['name']}")
            
            # Extract dietary restrictions
            for restriction in ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free']:
                if restriction in message_lower:
                    if restriction not in memory['dietary_restrictions']:
                        memory['dietary_restrictions'].append(restriction)
            
            # Track topics
            for topic in ['pasta', 'pizza', 'seafood', 'salad', 'dessert']:
                if topic in message_lower:
                    if topic not in memory['topics']:
                        memory['topics'].append(topic)
            
            # Add to history
            memory['history'].append({
                'query': message,
                'response': response[:200],  # Limit response length
                'timestamp': datetime.now().isoformat()
            })
            
            # Keep only last 10 exchanges
            memory['history'] = memory['history'][-10:]
            
        except Exception as e:
            logger.error(f"Memory extraction error: {e}")
            logger.error(traceback.format_exc())
        
        return memory
    
    def build_context_sections(self, db: Session, restaurant_id: str, query: str, 
                              query_type: QueryType, memory: Dict) -> Dict[ContextSection, str]:
        """Build context sections like enhanced version"""
        context_sections = {}
        
        try:
            # Add personalization section
            if memory['name'] or memory['dietary_restrictions']:
                personal_parts = []
                if memory['name']:
                    personal_parts.append(f"Customer name: {memory['name']}")
                if memory['dietary_restrictions']:
                    personal_parts.append(f"Dietary restrictions: {', '.join(memory['dietary_restrictions'])}")
                if memory['topics']:
                    personal_parts.append(f"Interested in: {', '.join(memory['topics'][:3])}")
                
                context_sections[ContextSection.PERSONALIZATION] = "\n".join(personal_parts)
            
            # Add conversation history
            if memory['history'] and len(memory['history']) > 1:  # More than current
                history_parts = ["Recent conversation:"]
                for item in memory['history'][-3:-1]:  # Exclude current
                    history_parts.append(f"Customer: {item['query']}")
                    history_parts.append(f"Assistant: {item['response'][:100]}...")
                context_sections[ContextSection.CONVERSATION_HISTORY] = "\n".join(history_parts)
            
            # Skip menu for pure greetings
            # Removed GREETING special case - let AI handle naturally

            if False:  # was query_type == QueryType.GREETING
                pass
            
            # Menu search
            try:
                items = self.embedding_service.search_similar_items(
                    db=db,
                    restaurant_id=restaurant_id,
                    query=query,
                    limit=10,
                    threshold=0.35
                )
                
                if items:
                    menu_context = "Relevant menu items:\n"
                    for item in items:
                        menu_context += f"- {item['name']} (${item['price']})\n"
                    context_sections[ContextSection.MENU_ITEMS] = menu_context
                    
            except Exception as e:
                logger.warning(f"Menu search failed: {e}")
            
        except Exception as e:
            logger.error(f"Context building error: {e}")
            logger.error(traceback.format_exc())
        
        return context_sections
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat with comprehensive error handling"""
        
        try:
            # Skip AI for restaurant messages
            if req.sender_type == 'restaurant':
                return ChatResponse(answer="")
            
            # Get memory FIRST (critical for working across messages)
            memory = self.get_memory(req.restaurant_id, req.client_id)
            logger.info(f"Retrieved memory: name={memory.get('name')}, history={len(memory.get('history', []))}")
            
            # Pre-extract from current message
            memory = self.extract_and_update_memory(memory, req.message, "")
            
            # Classify query and detect language
            query_type = HybridQueryClassifier.classify(req.message)
            language = detect_language(req.message)
            
            # Get restaurant
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                return ChatResponse(answer="Restaurant not found.")
            
            business_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
            
            # Build context sections
            context_sections = self.build_context_sections(
                db, req.restaurant_id, req.message, query_type, memory
            )
            
            # Create enhanced system prompt
            persona_name = get_persona_name(language)
            
            # Build personalized prompt
            if memory['name']:
                system_prompt = f"""You are {persona_name}, a friendly AI assistant for {business_name}.

You are speaking with {memory['name']}. Use their name naturally in your responses.
Be warm, personal, and helpful."""
            else:
                system_prompt = f"""You are {persona_name}, a friendly AI assistant for {business_name}.

Be warm and helpful. If the customer introduces themselves, acknowledge their name warmly."""
            
            # Add dietary awareness
            if memory['dietary_restrictions']:
                system_prompt += f"\n\nIMPORTANT: This customer follows a {', '.join(memory['dietary_restrictions'])} diet."
            
            # Add rules
            system_prompt += f"""

RULES:
1. Only recommend items that exist in the menu context provided
2. Be conversational and natural
3. Keep responses concise but helpful
4. Always respond in {language}"""
            
            # Format with context formatter
            full_prompt = context_formatter.format_prompt_with_context(
                system_prompt=system_prompt,
                context_sections=context_sections,
                customer_message=req.message,
                assistant_name=persona_name
            )
            
            # Get response with appropriate parameters
            params = get_hybrid_parameters(query_type)
            
            # Personalize temperature
            if memory['name'] or memory['dietary_restrictions']:
                params['temperature'] = 0.8
            
            # Get AI response
            answer = get_mia_response_hybrid(full_prompt, params)
            
            # Skip response validation to avoid issues
            # answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
            
            # Update memory with full exchange
            memory = self.extract_and_update_memory(memory, req.message, answer)
            
            # Save updated memory for next time
            self.save_memory(req.restaurant_id, req.client_id, memory)
            logger.info(f"Memory save completed: name={memory.get('name')}, dietary={memory.get('dietary_restrictions')}")
            
            # Save to database
            try:
                new_message = models.ChatMessage(
                    restaurant_id=req.restaurant_id,
                    client_id=req.client_id,
                    sender_type="ai",
                    message=answer
                )
                db.add(new_message)
                db.commit()
            except Exception as e:
                logger.error(f"Database save error: {e}")
                db.rollback()
            
            return ChatResponse(
                answer=answer,
                timestamp=req.message
            )
            
        except Exception as e:
            logger.error(f"Fixed memory RAG error: {e}")
            logger.error(traceback.format_exc())
            # Return a fallback response
            return ChatResponse(
                answer="I apologize, but I'm having technical difficulties. Please try again or ask our staff for assistance.",
                timestamp=req.message if req else ""
            )

# Create singleton
fixed_memory_rag = FixedMemoryRAG()