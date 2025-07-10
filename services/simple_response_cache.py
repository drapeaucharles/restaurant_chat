"""
Simple in-memory cache for common restaurant queries to reduce API calls.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple
import hashlib

class SimpleResponseCache:
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Tuple[str, datetime]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        
        # Common query patterns and their responses
        self.common_patterns = {
            "hours": ["open", "close", "when", "time", "hours"],
            "location": ["where", "address", "location", "find"],
            "contact": ["phone", "call", "email", "contact"],
            "wifi": ["wifi", "wi-fi", "internet", "password"],
            "parking": ["parking", "park", "car"],
            "reservation": ["reservation", "book", "table", "reserve"],
            "delivery": ["delivery", "deliver", "takeout", "take out", "pickup"],
            "payment": ["pay", "card", "cash", "credit", "debit"],
            "dietary": ["vegan", "vegetarian", "gluten", "allerg", "dairy", "nut"],
            "greeting": ["hi", "hello", "hey", "good morning", "good evening"]
        }
    
    def _get_cache_key(self, restaurant_id: str, message: str) -> str:
        """Generate a cache key from restaurant ID and normalized message."""
        normalized = message.lower().strip()
        # Remove punctuation and extra spaces
        normalized = ' '.join(normalized.split())
        combined = f"{restaurant_id}:{normalized}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def _is_similar_query(self, message1: str, message2: str) -> bool:
        """Check if two messages are similar enough to use cached response."""
        words1 = set(message1.lower().split())
        words2 = set(message2.lower().split())
        
        # If short messages, require exact match
        if len(words1) < 3 or len(words2) < 3:
            return words1 == words2
            
        # For longer messages, check overlap
        overlap = len(words1 & words2)
        total = len(words1 | words2)
        
        return overlap / total > 0.7 if total > 0 else False
    
    def get_query_type(self, message: str) -> Optional[str]:
        """Identify the type of query for better caching."""
        message_lower = message.lower()
        
        for query_type, keywords in self.common_patterns.items():
            if any(keyword in message_lower for keyword in keywords):
                return query_type
        
        return None
    
    def get(self, restaurant_id: str, message: str) -> Optional[str]:
        """Get cached response if available and not expired."""
        key = self._get_cache_key(restaurant_id, message)
        
        if key in self.cache:
            response, timestamp = self.cache[key]
            if datetime.now() - timestamp < self.ttl:
                return response
            else:
                # Remove expired entry
                del self.cache[key]
        
        # Check for similar queries
        query_type = self.get_query_type(message)
        if query_type:
            # Look for recent similar queries of the same type
            for cached_key, (response, timestamp) in list(self.cache.items()):
                if datetime.now() - timestamp < self.ttl:
                    # Extract restaurant_id from key
                    if cached_key.startswith(hashlib.md5(f"{restaurant_id}:".encode()).hexdigest()[:8]):
                        return response
        
        return None
    
    def set(self, restaurant_id: str, message: str, response: str) -> None:
        """Cache a response with timestamp."""
        # Only cache if response is substantial and not an error
        if len(response) > 20 and "error" not in response.lower() and "sorry" not in response.lower():
            key = self._get_cache_key(restaurant_id, message)
            self.cache[key] = (response, datetime.now())
            
            # Limit cache size
            if len(self.cache) > 1000:
                # Remove oldest entries
                sorted_items = sorted(self.cache.items(), key=lambda x: x[1][1])
                for old_key, _ in sorted_items[:100]:
                    del self.cache[old_key]
    
    def clear_expired(self) -> None:
        """Remove all expired entries."""
        current_time = datetime.now()
        expired_keys = [
            key for key, (_, timestamp) in self.cache.items()
            if current_time - timestamp >= self.ttl
        ]
        for key in expired_keys:
            del self.cache[key]

# Global cache instance
response_cache = SimpleResponseCache(ttl_minutes=30)