"""
Universal Memory Service - Works for any business type
Based on v4 but business-agnostic
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
from services.embedding_service_universal import universal_embedding_service as embedding_service
from services.response_validator_universal import universal_response_validator as response_validator
from services.redis_helper import redis_client
import models
import re
import json
from datetime import datetime

logger = logging.getLogger(__name__)

# Global memory store as backup
MEMORY_STORE = {}

class UniversalMemoryRAG:
    """Universal memory service for any business type"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        
    def get_memory_key(self, business_id: str, client_id: str) -> str:
        """Get memory key"""
        return f"universal_memory:{business_id}:{client_id}"
    
    def get_memory(self, business_id: str, client_id: str) -> Dict:
        """Get memory with fallback"""
        key = self.get_memory_key(business_id, client_id)
        
        # Try Redis first
        try:
            data = redis_client.get(key)
            if data:
                return json.loads(data)
        except Exception as e:
            logger.warning(f"Redis get failed: {e}")
        
        # Universal memory structure
        return MEMORY_STORE.get(key, {
            'name': None,
            'history': [],
            'preferences': [],
            'requirements': [],  # Generic term for any business needs
            'interests': [],     # What they're interested in
            'context': {}        # Business-specific data
        })
    
    def save_memory(self, business_id: str, client_id: str, memory: Dict):
        """Save memory with fallback"""
        key = self.get_memory_key(business_id, client_id)
        
        # Save to local store first
        MEMORY_STORE[key] = memory
        
        # Try Redis
        try:
            redis_client.setex(key, 14400, json.dumps(memory))  # 4 hours
        except Exception as e:
            logger.warning(f"Redis save failed: {e}")
    
    def extract_requirements(self, message: str, business_type: str) -> List[str]:
        """Extract requirements based on business type"""
        message_lower = message.lower()
        requirements = []
        
        # Universal patterns
        universal_patterns = {
            'budget': ['budget', 'price range', 'cost', 'affordable', 'expensive'],
            'timeline': ['urgent', 'asap', 'deadline', 'by tomorrow', 'next week'],
            'quality': ['high quality', 'premium', 'basic', 'professional', 'simple'],
            'location': ['near me', 'delivery', 'pickup', 'remote', 'in-person']
        }
        
        # Business-specific patterns
        if business_type == 'restaurant':
            patterns = {
                'dietary': ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free', 'kosher', 'halal', 'allergic'],
                'meal_type': ['breakfast', 'lunch', 'dinner', 'brunch', 'dessert', 'appetizer'],
                'cuisine': ['italian', 'mexican', 'chinese', 'japanese', 'american', 'indian']
            }
        elif business_type == 'hotel':
            patterns = {
                'room_type': ['suite', 'single', 'double', 'king', 'queen', 'view'],
                'amenities': ['wifi', 'parking', 'pool', 'gym', 'spa', 'breakfast included'],
                'duration': ['night', 'week', 'weekend', 'extended stay']
            }
        elif business_type == 'salon':
            patterns = {
                'service': ['haircut', 'color', 'highlights', 'manicure', 'pedicure', 'facial'],
                'style': ['modern', 'classic', 'trendy', 'natural', 'bold'],
                'time': ['morning', 'afternoon', 'evening', 'weekend']
            }
        elif business_type == 'repair':
            patterns = {
                'device': ['phone', 'laptop', 'computer', 'tablet', 'screen', 'battery'],
                'issue': ['broken', 'cracked', 'slow', 'not working', 'damaged'],
                'warranty': ['warranty', 'guarantee', 'insurance']
            }
        else:
            # Generic business patterns
            patterns = {
                'service_type': ['consultation', 'service', 'product', 'appointment'],
                'preference': ['prefer', 'like', 'want', 'need', 'looking for']
            }
        
        # Combine universal and business-specific patterns
        all_patterns = {**universal_patterns, **patterns}
        
        # Extract requirements
        for category, keywords in all_patterns.items():
            for keyword in keywords:
                if keyword in message_lower:
                    requirements.append(f"{category}:{keyword}")
        
        return requirements
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat with universal memory"""
        
        # Get business (using restaurant_id as business_id for compatibility)
        business_id = req.restaurant_id
        
        # Get existing memory FIRST
        memory = self.get_memory(business_id, req.client_id)
        logger.info(f"Universal: Retrieved memory for {req.client_id}: name={memory.get('name')}, history={len(memory.get('history', []))}")
        
        # Extract name from current message
        name_match = re.search(r'my name is (\w+)', req.message, re.IGNORECASE)
        if name_match:
            memory['name'] = name_match.group(1).capitalize()
            logger.info(f"Universal: Captured name: {memory['name']}")
        
        # Classify query type
        try:
            query_type = HybridQueryClassifier.classify(req.message)
            language = detect_language(req.message)
            logger.info(f"Universal: Query type: {query_type.value}, Language: {language}")
        except Exception as e:
            logger.error(f"Universal: Classification failed: {e}")
            query_type = QueryType.GENERAL
            language = "en"
        
        # Get business info
        business = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == business_id
        ).first()
        
        if not business:
            return ChatResponse(answer="Business not found.")
        
        # Determine business type
        business_data = business.data or {}
        business_type = business_data.get('business_type', 'restaurant')  # Default to restaurant for compatibility
        business_name = business_data.get('name', 'our business')
        
        # Extract requirements based on business type
        new_requirements = self.extract_requirements(req.message, business_type)
        for req_item in new_requirements:
            if req_item not in memory.get('requirements', []):
                memory.setdefault('requirements', []).append(req_item)
                logger.info(f"Universal: Added requirement: {req_item}")
        
        # Build context
        context_parts = [f"Business: {business_name} ({business_type})"]
        
        # Add customer info if known
        if memory.get('name'):
            context_parts.append(f"Customer name: {memory['name']} (use their name in your response)")
        
        # Add recent history
        if memory.get('history'):
            context_parts.append("\nRecent conversation:")
            for item in memory['history'][-3:]:
                context_parts.append(f"Customer: {item['q']}")
                context_parts.append(f"You: {item['a'][:100]}...")
        
        # Add requirements
        if memory.get('requirements'):
            context_parts.append(f"\nCustomer requirements: {', '.join(memory['requirements'][-5:])}")
        
        # Add interests
        message_lower = req.message.lower()
        interest_keywords = ['interested in', 'looking for', 'need', 'want', 'searching for']
        for keyword in interest_keywords:
            if keyword in message_lower:
                interest = message_lower.split(keyword)[1].split('.')[0].strip()
                if interest and len(interest) < 50 and interest not in memory.get('interests', []):
                    memory.setdefault('interests', []).append(interest)
                    context_parts.append(f"\nInterested in: {interest}")
        
        # Get relevant items/services (works for any business)
        if query_type not in [QueryType.GREETING] and len(req.message) > 10:
            try:
                # For restaurants, check allergen service
                if business_type == 'restaurant' and any(word in message_lower for word in ['allerg', 'dietary'] + [r.split(':')[1] for r in memory.get('requirements', []) if r.startswith('dietary:')]):
                    # Import allergen service only when needed
                    from services.allergen_service import allergen_service
                    logger.info(f"Universal: Using allergen service for dietary query")
                    allergen_data = allergen_service.get_items_for_restriction(
                        db, business_id, message_lower
                    )
                    
                    if allergen_data['safe_items']:
                        context_parts.append(f"\nItems suitable for {allergen_data['restriction_type']}:")
                        for item in allergen_data['safe_items'][:5]:
                            context_parts.append(f"- {item['name']} (${item['price']})")
                else:
                    # Regular embedding search for any business
                    items = self.embedding_service.search_similar_items(
                        db=db,
                        restaurant_id=business_id,  # Works for any business
                        query=req.message,
                        limit=5,
                        threshold=0.35
                    )
                    
                    if items:
                        context_parts.append("\nRelevant items/services:")
                        for item in items:
                            context_parts.append(f"- {item['name']} (${item['price']})")
            except Exception as e:
                logger.warning(f"Universal: Search failed: {e}")
        
        # Build prompt
        context = "\n".join(context_parts)
        
        # Handle specific queries about name
        if ('my name' in message_lower or 'remember' in message_lower) and memory.get('name'):
            prompt = f"""{context}

Customer asked: {req.message}

You should acknowledge that you know their name is {memory['name']} and use it in your response.
Be friendly and professional."""
        else:
            prompt = f"""{context}

Customer: {req.message}

Instructions:
- Be friendly and professional
- If you know the customer's name, use it naturally
- Keep responses concise and helpful
- Only mention items/services from the context
- Adapt your tone to the business type ({business_type})

Response:"""
        
        # Get AI response
        try:
            params = get_hybrid_parameters(query_type)
            logger.info(f"Universal: Using params for {query_type.value}: {params}")
        except Exception as e:
            logger.error(f"Universal: Failed to get params: {e}")
            params = {
                'max_tokens': 200,
                'temperature': 0.7
            }
        
        answer = get_mia_response_hybrid(prompt, params)
        
        # Validate response (for any business)
        try:
            logger.info(f"Universal: Validating response...")
            validated_answer = response_validator.validate_and_correct(answer, db, business_id)
            if answer != validated_answer:
                logger.info(f"Universal: Response was modified by validator")
            answer = validated_answer
        except Exception as e:
            logger.error(f"Universal: Response validation failed: {e}")
        
        # Update history
        memory.setdefault('history', []).append({
            'q': req.message,
            'a': answer,
            'time': datetime.now().isoformat(),
            'query_type': query_type.value,
            'business_type': business_type
        })
        
        # Keep only last 10 exchanges
        memory['history'] = memory['history'][-10:]
        
        # Save memory for next time
        self.save_memory(business_id, req.client_id, memory)
        logger.info(f"Universal: Saved memory for {req.client_id}: name={memory.get('name')}, requirements={len(memory.get('requirements', []))}")
        
        return ChatResponse(
            answer=answer,
            timestamp=req.message
        )

# Create singleton
universal_memory_rag = UniversalMemoryRAG()