"""
Enhanced conversation memory with lazy Redis import
This version will work even if Redis is not installed
"""
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
import json
import logging
from dataclasses import dataclass, asdict
from enum import Enum
from services.redis_helper import redis_client

logger = logging.getLogger(__name__)

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
    """Manages conversation memory with automatic Redis/in-memory fallback"""
    
    def __init__(self):
        self.max_memory_items = 10  # Keep last 10 full interactions
        self.memory_duration = timedelta(hours=4)
        self.local_memory = {}  # Always maintain local cache
        
    def _get_key(self, restaurant_id: str, client_id: str) -> str:
        """Generate Redis key for conversation"""
        return f"conv:{restaurant_id}:{client_id}"
    
    def add_turn(self, restaurant_id: str, client_id: str, query: str, response: str, metadata: Dict = None):
        """Add a conversation turn"""
        key = self._get_key(restaurant_id, client_id)
        turn = ConversationTurn(query, response, metadata)
        
        # Get existing history
        history = self.get_history(restaurant_id, client_id)
        history.append(turn)
        
        # Trim to max items
        if len(history) > self.max_memory_items:
            history = history[-self.max_memory_items:]
        
        # Store in local memory
        self.local_memory[key] = history
        
        # Try to store in Redis
        try:
            history_data = [turn.to_dict() for turn in history]
            redis_client.setex(
                key,
                int(self.memory_duration.total_seconds()),
                json.dumps(history_data)
            )
        except Exception as e:
            logger.debug(f"Redis storage failed, using local memory: {e}")
    
    def get_history(self, restaurant_id: str, client_id: str) -> List[ConversationTurn]:
        """Get conversation history"""
        key = self._get_key(restaurant_id, client_id)
        
        # Check local memory first
        if key in self.local_memory:
            return self.local_memory[key]
        
        # Try Redis
        try:
            data = redis_client.get(key)
            if data:
                history_data = json.loads(data)
                history = [ConversationTurn.from_dict(turn) for turn in history_data]
                self.local_memory[key] = history  # Cache locally
                return history
        except Exception as e:
            logger.debug(f"Redis retrieval failed: {e}")
        
        return []
    
    def get_context(self, restaurant_id: str, client_id: str, include_metadata: bool = False) -> str:
        """Get formatted context from conversation history"""
        history = self.get_history(restaurant_id, client_id)
        
        if not history:
            return ""
        
        context_parts = ["Previous conversation:"]
        for turn in history[-5:]:  # Last 5 turns
            context_parts.append(f"Customer: {turn.query}")
            context_parts.append(f"Assistant: {turn.response[:200]}...")
            if include_metadata and turn.metadata:
                context_parts.append(f"[Metadata: {turn.metadata}]")
        
        return "\n".join(context_parts)
    
    def extract_customer_info(self, restaurant_id: str, client_id: str) -> Dict[str, Any]:
        """Extract customer preferences and info from history"""
        history = self.get_history(restaurant_id, client_id)
        
        info = {
            'name': None,
            'preferences': [],
            'dietary_restrictions': [],
            'mentioned_items': [],
            'topics': []
        }
        
        # Simple extraction logic
        for turn in history:
            query_lower = turn.query.lower()
            
            # Extract name
            if 'my name is' in query_lower:
                import re
                name_match = re.search(r'my name is (\w+)', turn.query, re.IGNORECASE)
                if name_match:
                    info['name'] = name_match.group(1).capitalize()
            
            # Extract dietary restrictions
            for restriction in ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free']:
                if restriction in query_lower:
                    if restriction not in info['dietary_restrictions']:
                        info['dietary_restrictions'].append(restriction)
            
            # Extract preferences
            if 'i like' in query_lower or 'i love' in query_lower:
                info['preferences'].append(turn.query)
            
            # Track topics
            for topic in ['pasta', 'pizza', 'dessert', 'wine', 'appetizer', 'salad']:
                if topic in query_lower:
                    if topic not in info['topics']:
                        info['topics'].append(topic)
        
        return info
    
    def clear_history(self, restaurant_id: str, client_id: str):
        """Clear conversation history"""
        key = self._get_key(restaurant_id, client_id)
        
        # Clear local memory
        if key in self.local_memory:
            del self.local_memory[key]
        
        # Clear Redis
        try:
            redis_client.delete(key)
        except Exception as e:
            logger.debug(f"Redis clear failed: {e}")

# Create singleton instance
enhanced_conversation_memory = EnhancedConversationMemory()