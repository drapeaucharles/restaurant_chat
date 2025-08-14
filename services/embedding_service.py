"""
Embedding service for RAG implementation
Uses sentence-transformers for free, high-quality embeddings
"""
import os
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy import text
from sqlalchemy.orm import Session
import json

# Try to import ML libraries, but don't fail if they're not available
try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    ML_AVAILABLE = True
except ImportError:
    ML_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ML libraries not available. RAG features will be disabled.")

logger = logging.getLogger(__name__)

class EmbeddingService:
    """Service for creating and managing embeddings"""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model"""
        if not ML_AVAILABLE:
            logger.warning("ML libraries not available, embedding service disabled")
            self.model = None
            self.embedding_dim = 384  # Default for all-MiniLM-L6-v2
            return
            
        try:
            # Use cache dir to avoid re-downloading
            cache_dir = os.path.join(os.path.dirname(__file__), "..", "model_cache")
            os.makedirs(cache_dir, exist_ok=True)
            
            self.model = SentenceTransformer(model_name, cache_folder=cache_dir)
            self.embedding_dim = self.model.get_sentence_embedding_dimension()
            logger.info(f"Loaded embedding model: {model_name} (dim={self.embedding_dim})")
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            self.model = None
    
    def create_menu_item_text(self, item: Dict) -> str:
        """Create searchable text from menu item"""
        parts = []
        
        # Add name
        name = item.get('dish') or item.get('name', '')
        if name:
            parts.append(f"Dish: {name}")
        
        # Add description
        desc = item.get('description', '')
        if desc:
            parts.append(f"Description: {desc}")
        
        # Add category
        category = item.get('subcategory', '')
        if category:
            parts.append(f"Category: {category}")
        
        # Add ingredients
        ingredients = item.get('ingredients', [])
        if ingredients:
            parts.append(f"Ingredients: {', '.join(ingredients)}")
        
        # Add price
        price = item.get('price', '')
        if price:
            parts.append(f"Price: {price}")
        
        # Add dietary info
        dietary = []
        if item.get('vegetarian'):
            dietary.append('vegetarian')
        if item.get('vegan'):
            dietary.append('vegan')
        if item.get('gluten_free'):
            dietary.append('gluten-free')
        if dietary:
            parts.append(f"Dietary: {', '.join(dietary)}")
        
        return " | ".join(parts)
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding for text"""
        if not self.model:
            return None
        
        try:
            embedding = self.model.encode(text, convert_to_numpy=True)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return None
    
    def create_embeddings_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Create embeddings for multiple texts"""
        if not self.model or not texts:
            return None
        
        try:
            if ML_AVAILABLE:
                embeddings = self.model.encode(texts, convert_to_numpy=True, show_progress_bar=True)
                # Convert numpy array to list of lists
                return embeddings.tolist()
            else:
                # Return None if ML not available
                return None
        except Exception as e:
            logger.error(f"Failed to create batch embeddings: {e}")
            return None
    
    def index_restaurant_menu(self, db: Session, restaurant_id: str, menu_items: List[Dict]) -> int:
        """Index all menu items for a restaurant"""
        if not self.model:
            logger.error("Embedding model not loaded")
            return 0
        
        indexed = 0
        texts = []
        items_data = []
        
        # Prepare all texts and data
        for item in menu_items:
            item_id = item.get('id', str(hash(item.get('dish', ''))))
            name = item.get('dish') or item.get('name', '')
            
            if not name:
                continue
            
            full_text = self.create_menu_item_text(item)
            texts.append(full_text)
            
            items_data.append({
                'restaurant_id': restaurant_id,
                'item_id': str(item_id),
                'item_name': name,
                'item_description': item.get('description', ''),
                'item_price': item.get('price', ''),
                'item_category': item.get('subcategory', ''),
                'item_ingredients': item.get('ingredients', []),
                'dietary_tags': self._extract_dietary_tags(item),
                'full_text': full_text
            })
        
        if not texts:
            return 0
        
        # Create embeddings in batch
        logger.info(f"Creating embeddings for {len(texts)} menu items...")
        embeddings = self.create_embeddings_batch(texts)
        
        if embeddings is None:
            return 0
        
        # Insert into database
        for i, (item_data, embedding) in enumerate(zip(items_data, embeddings)):
            try:
                # embedding is already a list
                item_data['embedding'] = embedding
                
                # Upsert (insert or update)
                db.execute(text("""
                    INSERT INTO menu_embeddings 
                    (restaurant_id, item_id, item_name, item_description, item_price, 
                     item_category, item_ingredients, dietary_tags, full_text, embedding)
                    VALUES 
                    (:restaurant_id, :item_id, :item_name, :item_description, :item_price,
                     :item_category, :item_ingredients, :dietary_tags, :full_text, :embedding)
                    ON CONFLICT (restaurant_id, item_id) 
                    DO UPDATE SET
                        item_name = EXCLUDED.item_name,
                        item_description = EXCLUDED.item_description,
                        item_price = EXCLUDED.item_price,
                        item_category = EXCLUDED.item_category,
                        item_ingredients = EXCLUDED.item_ingredients,
                        dietary_tags = EXCLUDED.dietary_tags,
                        full_text = EXCLUDED.full_text,
                        embedding = EXCLUDED.embedding,
                        updated_at = CURRENT_TIMESTAMP
                """), item_data)
                
                indexed += 1
                
            except Exception as e:
                logger.error(f"Failed to index item {item_data['item_name']}: {e}")
        
        db.commit()
        logger.info(f"Indexed {indexed} menu items for restaurant {restaurant_id}")
        return indexed
    
    def search_similar_items(self, db: Session, restaurant_id: str, query: str, 
                           limit: int = 5, threshold: float = 0.3) -> List[Dict]:
        """Search for similar menu items using vector similarity"""
        if not self.model:
            return []
        
        # Create query embedding
        query_embedding = self.create_embedding(query)
        if not query_embedding:
            return []
        
        # Search using cosine similarity
        results = db.execute(text("""
            SELECT 
                item_id,
                item_name,
                item_description,
                item_price,
                item_category,
                item_ingredients,
                dietary_tags,
                1 - (embedding <=> :query_embedding::vector) as similarity
            FROM menu_embeddings
            WHERE restaurant_id = :restaurant_id
                AND 1 - (embedding <=> :query_embedding::vector) > :threshold
            ORDER BY similarity DESC
            LIMIT :limit
        """), {
            'restaurant_id': restaurant_id,
            'query_embedding': query_embedding,
            'threshold': threshold,
            'limit': limit
        })
        
        items = []
        for row in results:
            items.append({
                'item_id': row.item_id,
                'name': row.item_name,
                'description': row.item_description,
                'price': row.item_price,
                'category': row.item_category,
                'ingredients': row.item_ingredients or [],
                'dietary_tags': row.dietary_tags or [],
                'similarity': float(row.similarity)
            })
        
        return items
    
    def _extract_dietary_tags(self, item: Dict) -> List[str]:
        """Extract dietary tags from menu item"""
        tags = []
        
        if item.get('vegetarian'):
            tags.append('vegetarian')
        if item.get('vegan'):
            tags.append('vegan')
        if item.get('gluten_free'):
            tags.append('gluten-free')
        
        # Check description for dietary keywords
        desc = (item.get('description', '') + ' ' + item.get('name', '')).lower()
        if 'dairy-free' in desc or 'dairy free' in desc:
            tags.append('dairy-free')
        if 'nut-free' in desc or 'nut free' in desc:
            tags.append('nut-free')
        if 'spicy' in desc:
            tags.append('spicy')
        if 'mild' in desc:
            tags.append('mild')
        
        return tags

# Choose embedding service based on environment
USE_LIGHTWEIGHT = os.getenv("USE_LIGHTWEIGHT_EMBEDDINGS", "true").lower() == "true"

if USE_LIGHTWEIGHT:
    # Use lightweight service for Railway
    from .embedding_service_lite import lightweight_embedding_service
    embedding_service = lightweight_embedding_service
    logger.info("Using lightweight embedding service")
else:
    # Use full ML service if available
    embedding_service = EmbeddingService()
    logger.info("Using full ML embedding service")