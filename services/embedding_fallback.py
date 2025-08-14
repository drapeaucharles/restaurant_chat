"""
Fallback embedding service that works without pgvector
Uses hash-based similarity for basic semantic search
"""
import hashlib
import json
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

class FallbackEmbeddingService:
    """Fallback service when pgvector is not available"""
    
    def __init__(self):
        logger.info("Using fallback embedding service (no pgvector)")
    
    def create_hash_embedding(self, text: str) -> List[float]:
        """Create a simple hash-based 'embedding' for fallback"""
        # Create multiple hashes for better distribution
        hashes = []
        
        # Tokenize and normalize
        tokens = text.lower().split()
        
        # Create feature vector based on keywords
        features = {
            'healthy': ['healthy', 'light', 'fresh', 'salad', 'grilled', 'steamed'],
            'vegetarian': ['vegetarian', 'veggie', 'vegan', 'plant', 'tofu'],
            'pasta': ['pasta', 'spaghetti', 'fettuccine', 'penne', 'linguine', 'ravioli'],
            'seafood': ['seafood', 'fish', 'salmon', 'shrimp', 'lobster', 'crab'],
            'meat': ['beef', 'chicken', 'pork', 'steak', 'meat', 'lamb'],
            'spicy': ['spicy', 'hot', 'chili', 'pepper', 'jalapeño'],
            'comfort': ['comfort', 'hearty', 'rich', 'creamy', 'cheese'],
            'dessert': ['dessert', 'sweet', 'cake', 'ice cream', 'chocolate']
        }
        
        # Create feature vector
        vector = []
        for category, keywords in features.items():
            score = sum(1 for token in tokens if any(kw in token for kw in keywords))
            vector.append(float(score) / max(len(tokens), 1))
        
        # Pad to 384 dimensions with hash values
        while len(vector) < 384:
            hash_val = int(hashlib.md5(f"{text}_{len(vector)}".encode()).hexdigest()[:8], 16)
            vector.append(float(hash_val % 100) / 100.0)
        
        return vector[:384]
    
    def calculate_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate simple similarity between vectors"""
        # Use first 8 dimensions (feature categories) for similarity
        score = 0.0
        for i in range(min(8, len(vec1), len(vec2))):
            score += min(vec1[i], vec2[i])
        return min(score, 1.0)

# Create global instance
fallback_embedding_service = FallbackEmbeddingService()