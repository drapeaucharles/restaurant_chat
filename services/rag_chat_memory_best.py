"""
Best of Both Worlds - Working Memory + Advanced Features
Combines the working memory timing with enhanced features
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
from services.response_validator import response_validator
from services.allergen_service import allergen_service
from services.context_formatter import context_formatter, ContextSection
from services.redis_helper import redis_client
import models
import re
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Global memory store as backup
MEMORY_STORE = {}

class BestMemoryRAG:
    """Best version - Working memory with all advanced features"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
        
    def get_memory_key(self, restaurant_id: str, client_id: str) -> str:
        """Get memory key"""
        return f"best_memory:{restaurant_id}:{client_id}"
    
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
        except Exception as e:
            logger.warning(f"Redis save failed: {e}")
    
    def extract_and_update_memory(self, memory: Dict, message: str, response: str):
        """Extract information from current exchange and update memory"""
        message_lower = message.lower()
        
        # Extract name
        name_match = re.search(r'my name is (\w+)', message, re.IGNORECASE)
        if name_match:
            memory['name'] = name_match.group(1).capitalize()
            logger.info(f"Captured name: {memory['name']}")
        
        # Extract dietary restrictions
        for restriction in ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free', 'kosher', 'halal']:
            if restriction in message_lower:
                if restriction not in memory['dietary_restrictions']:
                    memory['dietary_restrictions'].append(restriction)
        
        # Extract preferences
        if 'i like' in message_lower or 'i love' in message_lower or 'favorite' in message_lower:
            if message not in memory['preferences']:
                memory['preferences'].append(message)
        
        # Track topics
        for topic in ['pasta', 'pizza', 'seafood', 'steak', 'salad', 'soup', 'dessert', 'wine', 'beer', 'cocktail', 'appetizer']:
            if topic in message_lower:
                if topic not in memory['topics']:
                    memory['topics'].append(topic)
        
        # Track mentioned items from response
        if '$' in response:  # Likely contains menu items with prices
            # Simple extraction of items with prices
            import re
            items = re.findall(r'([A-Za-z\s]+)\s*\(\$[\d.]+\)', response)
            for item in items[:5]:  # Limit to avoid too many
                item = item.strip()
                if item and item not in memory['mentioned_items']:
                    memory['mentioned_items'].append(item)
        
        # Add to history
        memory['history'].append({
            'query': message,
            'response': response,
            'timestamp': datetime.now().isoformat(),
            'query_type': HybridQueryClassifier.classify(message).value
        })
        
        # Keep only last 10 exchanges
        memory['history'] = memory['history'][-10:]
        
        return memory
    
    def build_context_sections(self, db: Session, restaurant_id: str, query: str, 
                              query_type: QueryType, memory: Dict) -> Dict[ContextSection, str]:
        """Build context sections like enhanced version"""
        context_sections = {}
        
        # Add personalization section
        if memory['name'] or memory['preferences'] or memory['dietary_restrictions']:
            personal_parts = []
            if memory['name']:
                personal_parts.append(f"Customer name: {memory['name']}")
            if memory['dietary_restrictions']:
                personal_parts.append(f"Dietary restrictions: {', '.join(memory['dietary_restrictions'])}")
            if memory['topics']:
                personal_parts.append(f"Interested in: {', '.join(memory['topics'][:5])}")
            if memory['mentioned_items']:
                personal_parts.append(f"Previously discussed: {', '.join(memory['mentioned_items'][:3])}")
            
            context_sections[ContextSection.PERSONALIZATION] = "\n".join(personal_parts)
        
        # Add conversation history
        if memory['history']:
            history_parts = ["Recent conversation:"]
            for item in memory['history'][-3:]:
                history_parts.append(f"Customer: {item['query']}")
                history_parts.append(f"Assistant: {item['response'][:100]}...")
            context_sections[ContextSection.CONVERSATION_HISTORY] = "\n".join(history_parts)
        
        # Skip menu for pure greetings
        # Removed GREETING special case - let AI handle naturally

        if False:  # was query_type == QueryType.GREETING
            pass
        
        # Menu search
        try:
            query_lower = query.lower()
            is_allergen_query = any(word in query_lower for word in [
                'allerg', 'nut', 'dairy', 'gluten', 'shellfish', 'vegetarian', 'vegan'
            ])
            
            if is_allergen_query:
                # Use allergen service
                allergen_data = allergen_service.get_items_for_restriction(db, restaurant_id, query_lower)
                if allergen_data['safe_items']:
                    menu_context = f"Items suitable for {allergen_data['restriction_type']}:\n"
                    for item in allergen_data['safe_items'][:10]:
                        menu_context += f"- {item['name']} (${item['price']}): {item['description'][:60]}...\n"
                    context_sections[ContextSection.DIETARY_INFO] = menu_context
            else:
                # Regular menu search
                items = self.embedding_service.search_similar_items(
                    db=db,
                    restaurant_id=restaurant_id,
                    query=query,
                    limit=self.max_context_items,
                    threshold=self.similarity_threshold
                )
                
                if items:
                    menu_context = "Relevant menu items:\n"
                    for item in items:
                        desc = item.get('description', '')[:60]
                        menu_context += f"- {item['name']} (${item['price']}): {desc}...\n"
                    context_sections[ContextSection.MENU_ITEMS] = menu_context
                    
        except Exception as e:
            logger.warning(f"Menu search failed: {e}")
        
        # Add restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == restaurant_id
        ).first()
        
        if restaurant and restaurant.data:
            info_parts = []
            if 'cuisine_type' in restaurant.data:
                info_parts.append(f"Cuisine: {restaurant.data['cuisine_type']}")
            if 'hours' in restaurant.data:
                info_parts.append(f"Hours: {restaurant.data['hours']}")
            if 'phone' in restaurant.data:
                info_parts.append(f"Phone: {restaurant.data['phone']}")
            
            if info_parts:
                context_sections[ContextSection.RESTAURANT_INFO] = "\n".join(info_parts)
        
        return context_sections
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat with best of both approaches"""
        
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
            system_prompt += f"\n\nIMPORTANT: This customer follows a {', '.join(memory['dietary_restrictions'])} diet. Always consider this in your recommendations."
        
        # Add topic awareness
        if memory['topics']:
            system_prompt += f"\n\nThis customer has shown interest in: {', '.join(memory['topics'][:3])}"
        
        # Add rules
        system_prompt += f"""

RULES:
1. Only recommend items that exist in the menu context provided
2. Be conversational and natural
3. Keep responses concise but helpful
4. Always respond in {language}
5. If you know dietary restrictions, proactively filter recommendations"""
        
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
        
        # Validate response
        answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
        
        # Update memory with full exchange
        memory = self.extract_and_update_memory(memory, req.message, answer)
        
        # Save updated memory for next time
        self.save_memory(req.restaurant_id, req.client_id, memory)
        logger.info(f"Saved memory: name={memory.get('name')}, dietary={memory.get('dietary_restrictions')}")
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(
            answer=answer,
            timestamp=req.message
        )

# Create singleton
best_memory_rag = BestMemoryRAG()