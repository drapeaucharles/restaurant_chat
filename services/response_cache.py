# services/response_cache.py

import hashlib
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

class ResponseCache:
    """
    Simple in-memory cache for common restaurant queries.
    Reduces API calls for frequently asked questions.
    """
    
    def __init__(self, ttl_minutes: int = 60):
        self.cache: Dict[str, Dict[str, Any]] = {}
        self.ttl = timedelta(minutes=ttl_minutes)
        
        # Common query patterns that should be cached
        self.cacheable_patterns = [
            "what.*gluten.*free",
            "vegetarian.*options",
            "vegan.*dishes",
            "opening.*hours",
            "do.*deliver",
            "parking",
            "wheelchair.*access",
            "kid.*friendly",
            "allergen.*information",
            "nut.*free",
            "dairy.*free",
            "halal",
            "kosher",
            "price.*range",
            "reservation",
            "dress.*code",
            "wifi",
            "outdoor.*seating",
            "private.*event",
            "catering"
        ]
    
    def _generate_cache_key(self, restaurant_id: str, query: str) -> str:
        """Generate a unique cache key for the query."""
        # Normalize query: lowercase, strip whitespace, remove punctuation
        normalized_query = query.lower().strip()
        normalized_query = ''.join(c for c in normalized_query if c.isalnum() or c.isspace())
        normalized_query = ' '.join(normalized_query.split())  # Normalize whitespace
        
        # Create hash of restaurant_id + normalized query
        key_string = f"{restaurant_id}:{normalized_query}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _is_cacheable(self, query: str) -> bool:
        """Check if the query matches cacheable patterns."""
        import re
        query_lower = query.lower()
        
        # Check if query matches any cacheable pattern
        for pattern in self.cacheable_patterns:
            if re.search(pattern, query_lower):
                return True
        
        # Also cache very short, common queries
        common_exact_queries = [
            "menu", "hours", "location", "contact", "delivery",
            "takeout", "reservations", "specials", "happy hour"
        ]
        
        normalized = query_lower.strip().rstrip('?').rstrip('.')
        if normalized in common_exact_queries:
            return True
            
        return False
    
    def get(self, restaurant_id: str, query: str) -> Optional[Dict[str, Any]]:
        """
        Get cached response if available and not expired.
        Returns None if not cached or expired.
        """
        if not self._is_cacheable(query):
            return None
            
        cache_key = self._generate_cache_key(restaurant_id, query)
        
        if cache_key in self.cache:
            cached_item = self.cache[cache_key]
            
            # Check if expired
            if datetime.utcnow() < cached_item['expires_at']:
                print(f"💾 Cache HIT for query: '{query[:50]}...'")
                return cached_item['response']
            else:
                # Remove expired item
                del self.cache[cache_key]
                print(f"🗑️ Cache expired for query: '{query[:50]}...'")
        
        return None
    
    def set(self, restaurant_id: str, query: str, response: Dict[str, Any]) -> None:
        """
        Cache a response if the query is cacheable.
        """
        if not self._is_cacheable(query):
            return
            
        cache_key = self._generate_cache_key(restaurant_id, query)
        
        self.cache[cache_key] = {
            'response': response,
            'expires_at': datetime.utcnow() + self.ttl,
            'query': query,
            'restaurant_id': restaurant_id
        }
        
        print(f"💾 Cached response for query: '{query[:50]}...'")
        
        # Clean up old entries if cache is getting large
        if len(self.cache) > 1000:
            self._cleanup_expired()
    
    def _cleanup_expired(self) -> None:
        """Remove expired entries from cache."""
        now = datetime.utcnow()
        expired_keys = [
            key for key, item in self.cache.items()
            if now >= item['expires_at']
        ]
        
        for key in expired_keys:
            del self.cache[key]
        
        print(f"🧹 Cleaned up {len(expired_keys)} expired cache entries")
    
    def clear_restaurant_cache(self, restaurant_id: str) -> None:
        """Clear all cached responses for a specific restaurant."""
        keys_to_remove = [
            key for key, item in self.cache.items()
            if item['restaurant_id'] == restaurant_id
        ]
        
        for key in keys_to_remove:
            del self.cache[key]
            
        print(f"🗑️ Cleared {len(keys_to_remove)} cache entries for restaurant {restaurant_id}")

# Global cache instance
response_cache = ResponseCache(ttl_minutes=60)