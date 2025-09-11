"""
Dummy embedding service - no ML libraries needed
Used when RAG is not required (e.g., with v5 internal tools)
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class DummyEmbeddingService:
    """Dummy service that doesn't use ML libraries"""
    
    def __init__(self, model_name: str = "dummy"):
        """Initialize without loading any ML models"""
        self.model = None
        self.embedding_dim = 384
        logger.info("Using dummy embedding service (no ML libraries needed)")
    
    def create_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Return dummy embeddings"""
        return [[0.0] * self.embedding_dim for _ in texts]
    
    def search_similar_items(self, *args, **kwargs):
        """Return empty results"""
        return []
    
    def update_restaurant_embeddings(self, *args, **kwargs):
        """No-op"""
        pass
    
    def get_similar_categories(self, *args, **kwargs):
        """Return empty results"""
        return []

# Create global instance
dummy_embedding_service = DummyEmbeddingService()