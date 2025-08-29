"""
Enhanced conversation memory with full history tracking and better context
Fixed version with proper Redis fallback
"""
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum

logger = logging.getLogger(__name__)

# Try to import redis, but make it truly optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    logger.warning("Redis not available, using in-memory conversation storage")
    REDIS_AVAILABLE = False
    # Create a mock Redis class
    class MockRedis:
        def __init__(self, **kwargs):
            self.data = {}
        
        def ping(self):
            return True
        
        def get(self, key):
            return self.data.get(key)
        
        def setex(self, key, ttl, value):
            self.data[key] = value
            return True
    
    redis = type('redis', (), {'Redis': MockRedis})()

class ConversationTurn:
    """Represents a single turn in the conversation"""
    def __init__(self, query: str, response: str, metadata: Dict = None):
        self.query = query
        self.response = response
        self.timestamp = datetime.now().isoformat()
        self.metadata = metadata or {}
        
    def to_dict(self):
        return {
            'query': self.query,
            'response': self.response,
            'timestamp': self.timestamp,
            'metadata': self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict):
        turn = cls(data['query'], data['response'], data.get('metadata', {}))
        turn.timestamp = data['timestamp']
        return turn

class EnhancedConversationMemory:
    """Enhanced conversation memory with full history and intelligent summarization"""
    
    def __init__(self):
        self.max_memory_items = 10  # Keep last 10 full interactions
        self.memory_duration = timedelta(hours=4)  # Remember for 4 hours
        self.context_window = 5  # Use last 5 messages for context
        
        if REDIS_AVAILABLE:
            try:
                import os
                redis_url = os.getenv('REDIS_URL')
                if redis_url:
                    self.redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=2
                    )
                else:
                    self.redis_client = redis.Redis(
                        host='localhost',
                        port=6379,
                        decode_responses=True,
                        socket_connect_timeout=2
                    )
                self.redis_client.ping()
                self.redis_available = True
                logger.info("Redis connected for conversation memory")
            except Exception as e:
                logger.warning(f"Redis connection failed, using in-memory storage: {e}")
                self.redis_available = False
                self.memory_store = {}
        else:
            self.redis_available = False
            self.memory_store = {}
            logger.info("Using in-memory conversation storage")
    
    def remember(self, client_id: str, restaurant_id: str, 
                 query: str, response: str, metadata: Dict = None):
        """Store a full conversation turn"""
        memory_key = f"conv_mem_v2:{restaurant_id}:{client_id}"
        
        turn = ConversationTurn(query, response, metadata)
        
        if self.redis_available:
            try:
                # Get existing memory
                existing = self.redis_client.get(memory_key)
                if existing:
                    memory_list = [ConversationTurn.from_dict(item) 
                                  for item in json.loads(existing)]
                else:
                    memory_list = []
                
                # Add new turn and trim to max size
                memory_list.append(turn)
                memory_list = memory_list[-self.max_memory_items:]
                
                # Store with TTL
                self.redis_client.setex(
                    memory_key,
                    int(self.memory_duration.total_seconds()),
                    json.dumps([t.to_dict() for t in memory_list])
                )
            except Exception as e:
                logger.error(f"Redis storage error: {e}")
                self._fallback_memory(memory_key, turn)
        else:
            self._fallback_memory(memory_key, turn)
    
    def _fallback_memory(self, memory_key: str, turn: ConversationTurn):
        """Fallback to in-memory storage"""
        if memory_key not in self.memory_store:
            self.memory_store[memory_key] = []
        
        self.memory_store[memory_key].append(turn)
        self.memory_store[memory_key] = self.memory_store[memory_key][-self.max_memory_items:]
    
    def recall(self, client_id: str, restaurant_id: str) -> List[ConversationTurn]:
        """Recall full conversation history"""
        memory_key = f"conv_mem_v2:{restaurant_id}:{client_id}"
        
        if self.redis_available:
            try:
                memory_data = self.redis_client.get(memory_key)
                if memory_data:
                    return [ConversationTurn.from_dict(item) 
                           for item in json.loads(memory_data)]
            except Exception as e:
                logger.error(f"Redis recall error: {e}")
        
        # Fallback to in-memory
        return self.memory_store.get(memory_key, [])
    
    def get_conversation_context(self, client_id: str, restaurant_id: str) -> str:
        """Get formatted conversation history for context"""
        memories = self.recall(client_id, restaurant_id)
        
        if not memories:
            return ""
        
        # Use last N messages for context
        recent_memories = memories[-self.context_window:]
        
        context_parts = []
        for i, turn in enumerate(recent_memories):
            context_parts.append(f"Customer: {turn.query}")
            # Include truncated response to save tokens
            response_preview = turn.response[:150] + "..." if len(turn.response) > 150 else turn.response
            context_parts.append(f"Assistant: {response_preview}")
        
        return "\n".join(context_parts)
    
    def get_context_summary(self, client_id: str, restaurant_id: str) -> str:
        """Get an intelligent summary of conversation context"""
        memories = self.recall(client_id, restaurant_id)
        
        if not memories:
            return ""
        
        # Extract patterns and preferences
        preferences = self.extract_preferences(memories)
        topics = self.extract_topics(memories)
        
        summary_parts = []
        
        # Check for customer name
        for turn in memories:
            if turn.metadata and turn.metadata.get('customer_name'):
                summary_parts.append(f"Customer name: {turn.metadata['customer_name']}")
                break
        
        if preferences['dietary_restrictions']:
            summary_parts.append(f"Dietary restrictions: {', '.join(preferences['dietary_restrictions'])}")
        
        if preferences['favorite_categories']:
            summary_parts.append(f"Interested in: {', '.join(preferences['favorite_categories'][:3])}")
        
        if preferences['price_sensitivity']:
            summary_parts.append(f"Price preference: {preferences['price_sensitivity']}")
        
        if preferences['spice_preference']:
            summary_parts.append(f"Spice preference: {preferences['spice_preference']}")
        
        if topics:
            summary_parts.append(f"Recent topics: {', '.join(topics[:3])}")
        
        return "; ".join(summary_parts) if summary_parts else ""
    
    def extract_preferences(self, memories: List[ConversationTurn]) -> Dict:
        """Extract customer preferences from conversation history"""
        preferences = {
            'dietary_restrictions': set(),
            'favorite_categories': [],
            'price_sensitivity': None,
            'spice_preference': None,
            'order_history': []
        }
        
        # Count category mentions
        category_mentions = {}
        
        for turn in memories:
            query_lower = turn.query.lower()
            response_lower = turn.response.lower()
            
            # Dietary restrictions
            if 'vegetarian' in query_lower:
                preferences['dietary_restrictions'].add('vegetarian')
            if 'vegan' in query_lower:
                preferences['dietary_restrictions'].add('vegan')
            if 'gluten' in query_lower:
                preferences['dietary_restrictions'].add('gluten-free')
            if 'allerg' in query_lower:
                # Try to extract specific allergen from metadata
                if turn.metadata.get('allergens'):
                    preferences['dietary_restrictions'].update(turn.metadata['allergens'])
            
            # Category interests
            for category in ['pasta', 'pizza', 'salad', 'dessert', 'appetizer', 'wine', 'cocktail']:
                if category in query_lower or category in response_lower:
                    category_mentions[category] = category_mentions.get(category, 0) + 1
            
            # Price sensitivity
            if any(word in query_lower for word in ['cheap', 'budget', 'affordable', 'inexpensive']):
                preferences['price_sensitivity'] = 'budget-conscious'
            elif any(word in query_lower for word in ['best', 'premium', 'special', 'finest']):
                preferences['price_sensitivity'] = 'quality-focused'
            
            # Spice preference
            if 'mild' in query_lower or 'not spicy' in query_lower:
                preferences['spice_preference'] = 'mild'
            elif 'spicy' in query_lower or 'hot' in query_lower:
                preferences['spice_preference'] = 'spicy'
            
            # Order history (if metadata contains order info)
            if turn.metadata.get('ordered_items'):
                preferences['order_history'].extend(turn.metadata['ordered_items'])
        
        # Sort categories by mention count
        preferences['favorite_categories'] = sorted(
            category_mentions.keys(), 
            key=lambda x: category_mentions[x], 
            reverse=True
        )
        
        # Convert set to list for JSON serialization
        preferences['dietary_restrictions'] = list(preferences['dietary_restrictions'])
        
        return preferences
    
    def extract_topics(self, memories: List[ConversationTurn]) -> List[str]:
        """Extract discussion topics from recent conversation"""
        topics = []
        
        topic_keywords = {
            'recommendations': ['recommend', 'suggest', 'what should', 'best'],
            'ingredients': ['contain', 'made with', 'ingredients', 'what\'s in'],
            'allergens': ['allerg', 'intolerant', 'can\'t eat', 'avoid'],
            'pricing': ['cost', 'price', 'how much', 'expensive'],
            'portions': ['size', 'portion', 'enough for', 'sharing'],
            'specials': ['special', 'today\'s', 'featured', 'promotion'],
            'dietary': ['vegetarian', 'vegan', 'gluten', 'healthy'],
            'location': ['where', 'location', 'address', 'how to get'],
            'hours': ['open', 'close', 'hours', 'when'],
            'reservations': ['book', 'reserve', 'table', 'reservation']
        }
        
        recent_queries = [m.query.lower() for m in memories[-5:]]
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in query for query in recent_queries for keyword in keywords):
                topics.append(topic)
        
        return topics
    
    def get_last_mentioned_items(self, client_id: str, restaurant_id: str, n: int = 3) -> List[str]:
        """Get the last N menu items mentioned in conversation"""
        memories = self.recall(client_id, restaurant_id)
        mentioned_items = []
        
        for turn in reversed(memories):
            # Extract items from metadata if available
            if turn.metadata.get('mentioned_items'):
                mentioned_items.extend(turn.metadata['mentioned_items'])
                if len(mentioned_items) >= n:
                    break
        
        return mentioned_items[:n]
    
    def should_clarify_context(self, client_id: str, restaurant_id: str, current_query: str) -> bool:
        """Determine if we should ask for clarification based on conversation history"""
        memories = self.recall(client_id, restaurant_id)
        
        if len(memories) < 1:
            return False
        
        # Check if current query references something ambiguous
        ambiguous_patterns = [
            (r'\b(it|that|this|those|them)\b', True),  # Pronouns without context
            (r'\b(the same|another one|more)\b', True),  # References to previous
            (r'how much does (it|that) cost', True),  # Price without item
            (r'is (it|that) (spicy|hot|mild)', True),  # Attributes without item
            (r"i'll (take|have|order) (it|that|this)", True),  # Orders without item
        ]
        
        query_lower = current_query.lower()
        
        # Check each pattern
        import re
        for pattern, needs_context in ambiguous_patterns:
            if re.search(pattern, query_lower):
                # Check if we have clear context from recent messages
                recent_items = self.get_last_mentioned_items(client_id, restaurant_id)
                
                # If no recent items mentioned and query is ambiguous, clarify
                if len(recent_items) == 0:
                    return True
                
                # Also check if it's been too long since last interaction
                if memories:
                    last_turn = memories[-1]
                    try:
                        from datetime import datetime
                        last_time = datetime.fromisoformat(last_turn.timestamp)
                        time_diff = datetime.now() - last_time
                        # If more than 5 minutes, context might be stale
                        if time_diff.total_seconds() > 300:
                            return True
                    except:
                        pass
                
                return False
        
        return False

# Singleton instance
enhanced_conversation_memory = EnhancedConversationMemory()