"""
Enhanced response cache with Redis support and in-memory fallback
"""
import redis
import json
import time
import os
from typing import Dict, Optional
from collections import OrderedDict
from threading import Lock
import hashlib
import logging

logger = logging.getLogger(__name__)

class InMemoryCache:
    """Thread-safe in-memory LRU cache as fallback"""
    
    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        self.cache = OrderedDict()
        self.timestamps = {}
        self.max_size = max_size
        self.ttl = ttl
        self.lock = Lock()
    
    def get(self, key: str) -> Optional[str]:
        with self.lock:
            if key in self.cache:
                # Check if expired
                if time.time() - self.timestamps[key] > self.ttl:
                    del self.cache[key]
                    del self.timestamps[key]
                    return None
                
                # Move to end (most recently used)
                self.cache.move_to_end(key)
                return self.cache[key]
            return None
    
    def set(self, key: str, value: str):
        with self.lock:
            # Remove oldest if at capacity
            if len(self.cache) >= self.max_size and key not in self.cache:
                oldest = next(iter(self.cache))
                del self.cache[oldest]
                del self.timestamps[oldest]
            
            self.cache[key] = value
            self.timestamps[key] = time.time()
            self.cache.move_to_end(key)
    
    def clear(self):
        with self.lock:
            self.cache.clear()
            self.timestamps.clear()

class HybridCache:
    """Cache with Redis primary and in-memory fallback"""
    
    def __init__(self, redis_host: str = "localhost", redis_port: int = 6379, 
                 redis_db: int = 0, ttl: int = 3600, redis_password: str = None):
        self.ttl = ttl
        self.in_memory = InMemoryCache(max_size=500, ttl=ttl)
        
        # Try to connect to Redis
        try:
            # Check for REDIS_URL first
            redis_url = os.getenv("REDIS_URL")
            if redis_url:
                self.redis_client = redis.from_url(redis_url, decode_responses=True)
            else:
                self.redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    db=redis_db,
                    password=redis_password,
                    decode_responses=True,
                    socket_connect_timeout=2,
                    socket_timeout=2
                )
            # Test connection
            self.redis_client.ping()
            self.redis_available = True
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.warning(f"Redis not available, using in-memory cache: {e}")
            self.redis_available = False
            self.redis_client = None
    
    def _generate_key(self, query: str, restaurant_id: str, query_type: str) -> str:
        """Generate cache key"""
        normalized = query.lower().strip()
        key_data = f"{restaurant_id}:{query_type}:{normalized}"
        hash_val = hashlib.md5(key_data.encode()).hexdigest()
        return f"chat:{hash_val}"
    
    def get(self, query: str, restaurant_id: str, query_type: str) -> Optional[str]:
        """Get from cache (Redis first, then in-memory)"""
        key = self._generate_key(query, restaurant_id, query_type)
        
        # Try Redis first
        if self.redis_available:
            try:
                value = self.redis_client.get(key)
                if value:
                    logger.debug(f"Redis cache hit for {query_type}")
                    # Also store in memory for faster access
                    self.in_memory.set(key, value)
                    return json.loads(value)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        # Fall back to in-memory
        value = self.in_memory.get(key)
        if value:
            logger.debug(f"Memory cache hit for {query_type}")
            return json.loads(value)
        
        return None
    
    def set(self, query: str, restaurant_id: str, query_type: str, response: str):
        """Set in both caches"""
        key = self._generate_key(query, restaurant_id, query_type)
        value = json.dumps(response)
        
        # Store in memory first (always works)
        self.in_memory.set(key, value)
        
        # Try Redis
        if self.redis_available:
            try:
                self.redis_client.setex(key, self.ttl, value)
                logger.debug(f"Cached in Redis: {query_type}")
            except Exception as e:
                logger.error(f"Redis set error: {e}")
    
    def clear(self):
        """Clear both caches"""
        self.in_memory.clear()
        if self.redis_available:
            try:
                # Clear only our keys
                keys = self.redis_client.keys("chat:*")
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
    
    def clear_pattern(self, pattern: str) -> int:
        """Clear cache entries matching pattern"""
        cleared = 0
        if self.redis_available:
            try:
                keys = self.redis_client.keys(f"chat:*{pattern}*")
                if keys:
                    self.redis_client.delete(*keys)
                    cleared = len(keys)
            except Exception as e:
                logger.error(f"Redis clear pattern error: {e}")
        return cleared
    
    def clear_all(self):
        """Clear all cache entries"""
        self.clear()
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        stats = {
            "redis_available": self.redis_available,
            "in_memory_entries": len(self.in_memory.cache),
            "in_memory_size": self.in_memory.max_size
        }
        
        if self.redis_available:
            try:
                info = self.redis_client.info()
                stats["redis_used_memory"] = info.get("used_memory_human", "unknown")
                stats["redis_connected_clients"] = info.get("connected_clients", 0)
            except:
                pass
        
        return stats

# Singleton instance
_cache_instance = None

def get_cache(redis_host: str = "localhost", redis_port: int = 6379, 
              redis_db: int = 0, ttl: int = 3600) -> HybridCache:
    """Get or create cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = HybridCache(redis_host, redis_port, redis_db, ttl)
    return _cache_instance