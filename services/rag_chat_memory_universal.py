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
from services.placeholder_remover import placeholder_remover
from sqlalchemy import text
import re
import json
from datetime import datetime
try:
    from .negation_detector import NegationDetector
except ImportError:
    NegationDetector = None

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
        
        # Use NegationDetector if available
        if NegationDetector:
            is_negative, negated_items = NegationDetector.detect_negation(message)
            preferences = NegationDetector.extract_preferences(message)
            
            # Add dislikes as requirements
            for dislike in preferences.get('dislikes', []):
                requirements.append(f"avoid:{dislike}")
            
            # Add likes as preferences
            for like in preferences.get('likes', []):
                requirements.append(f"prefer:{like}")
            
            # Check if it's a dietary restriction
            if NegationDetector.is_dietary_restriction(message):
                for dislike in preferences.get('dislikes', []):
                    requirements.append(f"dietary:{dislike}-free")
        
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
            logger.info(f"*** UNIVERSAL: NAME CAPTURED: {memory['name']} FROM MESSAGE: {req.message} ***")
            logger.info(f"*** MEMORY NOW CONTAINS NAME: {memory.get('name')} ***")
        
        # Classify query type
        try:
            query_type = HybridQueryClassifier.classify(req.message)
            language = detect_language(req.message)
            logger.info(f"Universal: Query type: {query_type.value}, Language: {language}")
        except Exception as e:
            logger.error(f"Universal: Classification failed: {e}")
            query_type = QueryType.GENERAL
            language = "en"
        
        # Get business info directly from businesses table
        business_query = text("""
            SELECT business_id, data, business_type, metadata 
            FROM businesses 
            WHERE business_id = :business_id
        """)
        result = db.execute(business_query, {"business_id": business_id}).fetchone()
        
        if not result:
            return ChatResponse(answer="Business not found.")
        
        # Extract business info
        business_id, business_data, business_type_db, metadata = result
        business_data = business_data or {}
        
        # Determine business type
        business_type = business_type_db or 'restaurant'  # Default to restaurant for compatibility
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
        if True and len(req.message) > 10:  # was query_type not in [QueryType.GREETING]
            try:
                found_specific_items = False
                
                # For restaurants, check allergen service
                if business_type == 'restaurant' and any(word in message_lower for word in ['allerg', 'dietary'] + [r.split(':')[1] for r in memory.get('requirements', []) if r.startswith('dietary:')]):
                    # Import allergen service only when needed
                    from services.allergen_service import allergen_service
                    logger.info(f"Universal: Using allergen service for dietary query")
                    suitable_items = allergen_service.get_items_for_dietary_need(
                        db, business_id, message_lower
                    )
                    
                    if suitable_items:
                        context_parts.append(f"\nItems suitable for your dietary needs:")
                        for item in suitable_items[:5]:
                            context_parts.append(f"- {item['name']} (${item['price']})")
                        found_specific_items = True
                else:
                    # Check for avoid requirements from memory
                    avoid_items = [req.split(':')[1] for req in memory.get('requirements', []) if req.startswith('avoid:')]
                    
                    # Regular embedding search for any business
                    items = self.embedding_service.search_similar_items(
                        db=db,
                        business_id=business_id,  # Fixed parameter name
                        query=req.message,
                        limit=10,  # Get more to filter
                        threshold=0.35
                    )
                    
                    if items:
                        # Filter out items with ingredients to avoid
                        if avoid_items:
                            filtered_items = []
                            for item in items:
                                # Check if item contains any avoided ingredients
                                item_desc = f"{item.get('name', '')} {item.get('description', '')}".lower()
                                if not any(avoid in item_desc for avoid in avoid_items):
                                    filtered_items.append(item)
                            items = filtered_items[:5]
                        
                        if items:
                            if avoid_items:
                                context_parts.append(f"\nRelevant items/services (avoiding {', '.join(avoid_items)}):")
                            else:
                                context_parts.append("\nRelevant items/services:")
                            for item in items:
                                context_parts.append(f"- {item['name']} (${item['price']})")
                            found_specific_items = True
                
                # IMPORTANT: If no specific items found, provide general menu context
                if not found_specific_items and business_type == 'restaurant':
                    # Check for negation in the query
                    negation_words = ["don't", "dont", "do not", "no ", "without", "avoid", "dislike", "hate", "allergic"]
                    is_negative = any(neg in message_lower for neg in negation_words)
                    
                    # Get all menu items for restaurants
                    all_items_query = text("""
                        SELECT name, price, description, category, ingredients, allergens
                        FROM menu_items 
                        WHERE business_id = :business_id
                        ORDER BY category, name
                        LIMIT 30
                    """)
                    all_items = db.execute(all_items_query, {"business_id": business_id}).fetchall()
                    
                    if all_items:
                        if is_negative:
                            context_parts.append("\nOur full menu (I'll help you find items without the ingredients you want to avoid):")
                        else:
                            context_parts.append("\nOur full menu includes:")
                            
                        current_category = None
                        for item in all_items:
                            if item.category != current_category:
                                current_category = item.category
                                context_parts.append(f"\n{current_category}:")
                            
                            desc_part = f": {item.description[:50]}..." if item.description else ""
                            ing_part = ""
                            if item.ingredients:
                                ingredients_list = json.loads(item.ingredients) if isinstance(item.ingredients, str) else item.ingredients
                                # For negative queries, highlight items that DON'T contain the unwanted ingredient
                                if ingredients_list:
                                    if is_negative:
                                        # Extract what they want to avoid
                                        unwanted_words = [w for w in message_lower.split() if len(w) > 3 and w not in negation_words]
                                        has_unwanted = any(unwanted in ing.lower() for unwanted in unwanted_words for ing in ingredients_list)
                                        if not has_unwanted:
                                            ing_part = " ✓ (safe choice)"
                                    else:
                                        # For positive queries about eggs
                                        if any('egg' in ing.lower() for ing in ingredients_list):
                                            ing_part = f" (contains: {', '.join(ingredients_list[:3])}...)"
                            
                            context_parts.append(f"- {item.name} (${item.price}){desc_part}{ing_part}")
                
            except Exception as e:
                logger.warning(f"Universal: Search/menu fetch failed: {e}")
        
        # Build prompt
        context = "\n".join(context_parts)
        
        # Handle specific queries about name
        if ('my name' in message_lower or 'remember' in message_lower) and memory.get('name'):
            logger.info(f"*** NAME QUERY DETECTED! Memory has name: {memory['name']} ***")
            prompt = f"""{context}

Customer asked: {req.message}

You should acknowledge that you know their name is {memory['name']} and use it in your response.
Be friendly and professional. NEVER use placeholder text."""
            logger.info(f"*** SPECIAL NAME PROMPT ACTIVATED ***")
        else:
            # Build strong instructions to prevent placeholders
            name_instruction = ""
            if memory.get('name'):
                name_instruction = f"The customer's name is {memory['name']}. Use it naturally in your response."
            else:
                name_instruction = "You don't know the customer's name yet. Start with a friendly greeting like 'Hello!' or 'Hi there!'"
            
            prompt = f"""{context}

Customer: {req.message}

CRITICAL INSTRUCTIONS:
- {name_instruction}
- NEVER EVER use placeholder text like [Customer's Name], [Your Name], [Business Name], etc.
- NEVER use brackets [] in your response
- If you don't know something, don't use a placeholder - just omit it or use generic language
- Be natural and conversational
- For legal/visa services, provide specific service information with prices when asked
- Keep responses helpful and concise

Examples of BAD responses (NEVER do this):
- "Hello [Customer's Name]" 
- "I'm [Your Name]"
- "Welcome to [Business Name]"

Examples of GOOD responses:
- "Hello! I'd be happy to help with your visa inquiry."
- "Hi there! For a 60-day stay, I recommend..."
- "Good day! Let me help you with that visa question."

Response:"""
        
        # Get AI response
        try:
            params = get_hybrid_parameters(query_type)
            logger.info(f"Universal: Using params for {query_type.value}: {params}")
            logger.info(f"UNIVERSAL MEMORY PROMPT BEING SENT:\n{prompt[:1000]}...")
        except Exception as e:
            logger.error(f"Universal: Failed to get params: {e}")
            params = {
                'max_tokens': 200,
                'temperature': 0.7
            }
        
        answer = get_mia_response_hybrid(prompt, params)
        
        # Remove any placeholders from the response
        answer = placeholder_remover.clean_response(answer, customer_name=memory.get('name'))
        
        # Double-check for placeholders
        if not placeholder_remover.validate_response(answer):
            logger.error(f"Response still contains placeholders: {answer[:100]}...")
            # Force clean it again
            answer = placeholder_remover.remove_placeholders(answer)
            if not answer.strip():
                # If cleaning removed everything, provide a generic response
                answer = "I'd be happy to help you with that. Could you please provide more details?"
        
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
        logger.info(f"*** UNIVERSAL: SAVING MEMORY FOR {req.client_id} ***")
        logger.info(f"*** MEMORY CONTENT: name={memory.get('name')}, history_count={len(memory.get('history', []))}, requirements={memory.get('requirements', [])} ***")
        logger.info(f"Universal: Saved memory for {req.client_id}: name={memory.get('name')}, requirements={len(memory.get('requirements', []))}")
        
        return ChatResponse(
            answer=answer,
            timestamp=req.message
        )

# Create singleton
universal_memory_rag = UniversalMemoryRAG()