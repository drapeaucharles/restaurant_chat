"""
Redis helper with lazy import to avoid import-time failures
"""
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class RedisClient:
    """Lazy Redis client that only imports when actually used"""
    
    def __init__(self):
        self._redis = None
        self._redis_available = None
        self._mock_storage = {}
    
    @property
    def redis(self):
        """Lazy load Redis only when accessed"""
        if self._redis_available is None:
            try:
                import redis
                import os
                
                # Check for Railway Redis configuration
                redis_url = os.getenv('REDIS_URL')
                redis_host = os.getenv('REDIS_HOST')
                
                if redis_url:
                    # Use Redis URL if available (Railway standard)
                    self._redis = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2
                    )
                    logger.info(f"Connecting to Redis via URL: {redis_url.split('@')[1] if '@' in redis_url else 'redis'}")
                elif redis_host:
                    # Use Redis host configuration
                    self._redis = redis.Redis(
                        host=redis_host,
                        port=int(os.getenv('REDIS_PORT', 6379)),
                        password=os.getenv('REDIS_PASSWORD'),
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2
                    )
                    logger.info(f"Connecting to Redis host: {redis_host}")
                else:
                    # Fallback to localhost
                    self._redis = redis.Redis(
                        host='localhost',
                        port=6379,
                        decode_responses=True,
                        socket_connect_timeout=2,
                        socket_timeout=2
                    )
                    logger.info("Connecting to local Redis")
                
                # Test connection
                self._redis.ping()
                self._redis_available = True
                logger.info("Redis connection established successfully")
            except Exception as e:
                logger.warning(f"Redis not available: {e}, using in-memory storage")
                self._redis_available = False
                self._redis = None
        
        return self._redis if self._redis_available else None
    
    def get(self, key: str) -> Optional[str]:
        """Get value with automatic fallback"""
        if self.redis:
            try:
                return self.redis.get(key)
            except Exception as e:
                logger.error(f"Redis get error: {e}")
        
        return self._mock_storage.get(key)
    
    def setex(self, key: str, ttl: int, value: str) -> bool:
        """Set value with TTL with automatic fallback"""
        if self.redis:
            try:
                return self.redis.setex(key, ttl, value)
            except Exception as e:
                logger.error(f"Redis setex error: {e}")
        
        self._mock_storage[key] = value
        return True
    
    def delete(self, key: str) -> bool:
        """Delete key with automatic fallback"""
        if self.redis:
            try:
                return bool(self.redis.delete(key))
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        if key in self._mock_storage:
            del self._mock_storage[key]
            return True
        return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists with automatic fallback"""
        if self.redis:
            try:
                return bool(self.redis.exists(key))
            except Exception as e:
                logger.error(f"Redis exists error: {e}")
        
        return key in self._mock_storage

# Global instance
redis_client = RedisClient()