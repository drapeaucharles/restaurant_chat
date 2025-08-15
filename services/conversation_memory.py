"""
Simple conversation memory to improve context awareness
"""
from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json
import redis

class ConversationMemory:
    """Lightweight conversation memory for better context"""
    
    def __init__(self):
        self.max_memory_items = 5  # Keep last 5 interactions
        self.memory_duration = timedelta(hours=2)  # Remember for 2 hours
        
        try:
            self.redis_client = redis.Redis(
                host='localhost',
                port=6379,
                decode_responses=True,
                socket_connect_timeout=2
            )
            self.redis_client.ping()
            self.redis_available = True
        except:
            self.redis_available = False
            self.memory_store = {}
    
    def remember(self, client_id: str, restaurant_id: str, 
                 query: str, response: str, metadata: Dict = None):
        """Store a conversation turn"""
        memory_key = f"conv_mem:{restaurant_id}:{client_id}"
        
        memory_item = {
            'query': query,
            'response': response[:200],  # Store only first 200 chars to save space
            'timestamp': datetime.now().isoformat(),
            'metadata': metadata or {}
        }
        
        if self.redis_available:
            # Get existing memory
            existing = self.redis_client.get(memory_key)
            if existing:
                memory_list = json.loads(existing)
            else:
                memory_list = []
            
            # Add new item and trim to max size
            memory_list.append(memory_item)
            memory_list = memory_list[-self.max_memory_items:]
            
            # Store with TTL
            self.redis_client.setex(
                memory_key,
                int(self.memory_duration.total_seconds()),
                json.dumps(memory_list)
            )
        else:
            # In-memory fallback
            if memory_key not in self.memory_store:
                self.memory_store[memory_key] = []
            
            self.memory_store[memory_key].append(memory_item)
            self.memory_store[memory_key] = self.memory_store[memory_key][-self.max_memory_items:]
    
    def recall(self, client_id: str, restaurant_id: str) -> List[Dict]:
        """Recall recent conversation history"""
        memory_key = f"conv_mem:{restaurant_id}:{client_id}"
        
        if self.redis_available:
            memory_data = self.redis_client.get(memory_key)
            if memory_data:
                return json.loads(memory_data)
        else:
            return self.memory_store.get(memory_key, [])
        
        return []
    
    def get_context_summary(self, client_id: str, restaurant_id: str) -> str:
        """Get a brief summary of recent conversation"""
        memories = self.recall(client_id, restaurant_id)
        
        if not memories:
            return ""
        
        # Extract key information
        recent_queries = [m['query'] for m in memories[-3:]]  # Last 3 queries
        
        # Look for patterns
        context_hints = []
        
        # Check for repeated interests
        all_text = " ".join(recent_queries).lower()
        
        if all_text.count("vegetarian") >= 2:
            context_hints.append("Customer has shown interest in vegetarian options")
        if all_text.count("spicy") >= 2:
            context_hints.append("Customer interested in spicy dishes")
        if "allerg" in all_text:
            context_hints.append("Customer has asked about allergens")
        if "wine" in all_text or "drink" in all_text:
            context_hints.append("Customer interested in beverages")
        
        if context_hints:
            return "Recent context: " + "; ".join(context_hints)
        
        return ""
    
    def extract_preferences(self, client_id: str, restaurant_id: str) -> Dict:
        """Extract learned preferences from conversation history"""
        memories = self.recall(client_id, restaurant_id)
        
        preferences = {
            'dietary_restrictions': set(),
            'favorite_categories': [],
            'price_sensitivity': None,
            'spice_preference': None
        }
        
        for memory in memories:
            query = memory['query'].lower()
            
            # Dietary restrictions
            if 'vegetarian' in query:
                preferences['dietary_restrictions'].add('vegetarian')
            if 'vegan' in query:
                preferences['dietary_restrictions'].add('vegan')
            if 'gluten' in query:
                preferences['dietary_restrictions'].add('gluten-free')
            
            # Price sensitivity
            if 'cheap' in query or 'budget' in query:
                preferences['price_sensitivity'] = 'budget-conscious'
            elif 'best' in query or 'special' in query:
                preferences['price_sensitivity'] = 'quality-focused'
            
            # Spice preference
            if 'mild' in query or 'not spicy' in query:
                preferences['spice_preference'] = 'mild'
            elif 'spicy' in query or 'hot' in query:
                preferences['spice_preference'] = 'spicy'
        
        # Convert set to list for JSON serialization
        preferences['dietary_restrictions'] = list(preferences['dietary_restrictions'])
        
        return preferences

# Singleton instance
conversation_memory = ConversationMemory()