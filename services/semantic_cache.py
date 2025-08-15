"""
Semantic caching system for improved response quality and speed
"""
from typing import Dict, List, Optional, Tuple
import json
import hashlib
from datetime import datetime, timedelta
import redis
import numpy as np
from services.embedding_service import embedding_service

class SemanticCache:
    """Cache responses based on semantic similarity, not exact matches"""
    
    def __init__(self):
        self.similarity_threshold = 0.85  # High threshold for cache hits
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
            self.memory_cache = {}
    
    def _get_cache_key(self, restaurant_id: str, query_embedding: List[float]) -> str:
        """Generate a cache key from restaurant and query embedding"""
        # Use first 8 dimensions of embedding for key (reduced dimensionality)
        embedding_str = ",".join([f"{x:.3f}" for x in query_embedding[:8]])
        return f"sem_cache:{restaurant_id}:{hashlib.md5(embedding_str.encode()).hexdigest()[:8]}"
    
    def find_similar_response(self, restaurant_id: str, query: str) -> Optional[Dict]:
        """Find a semantically similar cached response"""
        try:
            # Get query embedding
            query_embedding = embedding_service.create_embedding(query)
            
            if self.redis_available:
                # Get all cache entries for this restaurant
                pattern = f"sem_cache:{restaurant_id}:*"
                keys = self.redis_client.keys(pattern)
                
                best_match = None
                best_similarity = 0.0
                
                for key in keys[:50]:  # Limit to 50 most recent
                    cached = self.redis_client.get(key)
                    if cached:
                        data = json.loads(cached)
                        cached_embedding = data.get('embedding', [])
                        
                        # Calculate cosine similarity
                        similarity = self._cosine_similarity(query_embedding, cached_embedding)
                        
                        if similarity > best_similarity and similarity >= self.similarity_threshold:
                            best_similarity = similarity
                            best_match = data
                
                if best_match:
                    # Check if cache is still fresh (24 hours)
                    cached_time = datetime.fromisoformat(best_match['timestamp'])
                    if datetime.now() - cached_time < timedelta(hours=24):
                        return {
                            'response': best_match['response'],
                            'similarity': best_similarity,
                            'cached_query': best_match['query'],
                            'cache_hit': True
                        }
            
            return None
            
        except Exception as e:
            print(f"Semantic cache error: {e}")
            return None
    
    def store_response(self, restaurant_id: str, query: str, response: str, metadata: Dict = None):
        """Store a response with its semantic embedding"""
        try:
            # Get query embedding
            query_embedding = embedding_service.create_embedding(query)
            cache_key = self._get_cache_key(restaurant_id, query_embedding)
            
            cache_data = {
                'query': query,
                'response': response,
                'embedding': query_embedding,
                'timestamp': datetime.now().isoformat(),
                'metadata': metadata or {}
            }
            
            if self.redis_available:
                # Store with 48 hour TTL
                self.redis_client.setex(
                    cache_key,
                    172800,  # 48 hours in seconds
                    json.dumps(cache_data)
                )
            else:
                # Fallback to memory cache
                self.memory_cache[cache_key] = cache_data
                # Limit memory cache size
                if len(self.memory_cache) > 1000:
                    # Remove oldest entries
                    oldest_key = min(self.memory_cache.keys(), 
                                   key=lambda k: self.memory_cache[k]['timestamp'])
                    del self.memory_cache[oldest_key]
        
        except Exception as e:
            print(f"Error storing semantic cache: {e}")
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = sum(a * a for a in vec1) ** 0.5
        norm2 = sum(b * b for b in vec2) ** 0.5
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return dot_product / (norm1 * norm2)
    
    def get_response_variations(self, restaurant_id: str, query_type: str) -> List[str]:
        """Get varied responses for similar query types to improve diversity"""
        variations = {
            "greeting": [
                "Welcome! How may I assist you today?",
                "Hello! What can I help you find on our menu?",
                "Good to see you! What are you in the mood for?",
            ],
            "pasta_query": [
                "We have several delicious pasta options:",
                "Our pasta selection includes:",
                "Let me tell you about our pasta dishes:",
            ],
            "recommendation": [
                "Based on your preferences, I'd suggest:",
                "You might enjoy:",
                "I highly recommend:",
            ]
        }
        
        return variations.get(query_type, [])

# Singleton instance
semantic_cache = SemanticCache()