"""
Lightweight embedding service using HuggingFace API
No local ML models needed - perfect for Railway
"""
import os
import logging
import requests
from typing import List, Dict, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import json
import hashlib

logger = logging.getLogger(__name__)

class LightweightEmbeddingService:
    """Embedding service using HuggingFace Inference API"""
    
    def __init__(self):
        """Initialize with HuggingFace API"""
        self.api_key = os.getenv("HUGGINGFACE_API_KEY", "")
        self.model_id = "sentence-transformers/all-MiniLM-L6-v2"
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_id}"
        self.embedding_dim = 384
        
        if not self.api_key:
            logger.warning("No HuggingFace API key found. Using hash-based embeddings as fallback.")
            self.use_api = False
        else:
            self.use_api = True
            logger.info(f"Using HuggingFace API for embeddings: {self.model_id}")
    
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
        if self.use_api:
            return self._create_embedding_api(text)
        else:
            return self._create_embedding_fallback(text)
    
    def _create_embedding_api(self, text: str) -> Optional[List[float]]:
        """Create embedding using HuggingFace API"""
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            response = requests.post(
                self.api_url,
                headers=headers,
                json={"inputs": text, "options": {"wait_for_model": True}},
                timeout=30
            )
            
            if response.status_code == 200:
                # API returns embeddings directly
                embedding = response.json()
                if isinstance(embedding, list) and len(embedding) == self.embedding_dim:
                    return embedding
                elif isinstance(embedding, list) and len(embedding) > 0 and isinstance(embedding[0], list):
                    # Sometimes returns nested array
                    return embedding[0]
            else:
                logger.error(f"HuggingFace API error: {response.status_code} - {response.text}")
                return self._create_embedding_fallback(text)
                
        except Exception as e:
            logger.error(f"Failed to create embedding via API: {e}")
            return self._create_embedding_fallback(text)
    
    def _create_embedding_fallback(self, text: str) -> List[float]:
        """Create deterministic pseudo-embedding using hashing"""
        # This is a fallback - not as good as real embeddings but better than nothing
        # Creates a deterministic vector from text
        
        # Create multiple hash values
        hashes = []
        for i in range(self.embedding_dim // 32):  # 32 bits per hash
            hash_input = f"{text}:{i}".encode('utf-8')
            hash_value = int(hashlib.md5(hash_input).hexdigest(), 16)
            hashes.append(hash_value)
        
        # Convert to normalized floats
        embedding = []
        for h in hashes:
            # Extract 32 values from each hash
            for j in range(32):
                bit = (h >> j) & 1
                value = (bit * 2 - 1) * 0.1  # Small values between -0.1 and 0.1
                embedding.append(value)
        
        # Trim to exact dimension
        embedding = embedding[:self.embedding_dim]
        
        # Add some variety based on text features
        text_features = [
            len(text) / 1000.0,  # Length feature
            text.count(' ') / 100.0,  # Word count feature
            sum(ord(c) for c in text[:10]) / 10000.0  # Character sum feature
        ]
        
        for i, feature in enumerate(text_features):
            if i < len(embedding):
                embedding[i] += feature
        
        return embedding
    
    def create_embeddings_batch(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Create embeddings for multiple texts"""
        embeddings = []
        
        if self.use_api:
            # HuggingFace API supports batch processing
            try:
                headers = {"Authorization": f"Bearer {self.api_key}"}
                response = requests.post(
                    self.api_url,
                    headers=headers,
                    json={"inputs": texts, "options": {"wait_for_model": True}},
                    timeout=60
                )
                
                if response.status_code == 200:
                    embeddings = response.json()
                    if isinstance(embeddings, list) and len(embeddings) == len(texts):
                        return embeddings
                else:
                    logger.error(f"Batch API error: {response.status_code}")
                    # Fall back to individual processing
                    for text in texts:
                        emb = self.create_embedding(text)
                        if emb:
                            embeddings.append(emb)
                            
            except Exception as e:
                logger.error(f"Batch API failed: {e}")
                # Fall back to individual processing
                for text in texts:
                    emb = self.create_embedding(text)
                    if emb:
                        embeddings.append(emb)
        else:
            # Process individually with fallback
            for text in texts:
                emb = self.create_embedding(text)
                if emb:
                    embeddings.append(emb)
        
        return embeddings if embeddings else None
    
    def index_restaurant_menu(self, db: Session, restaurant_id: str, menu_items: List[Dict]) -> int:
        """Index all menu items for a restaurant"""
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
        
        # Create embeddings
        logger.info(f"Creating embeddings for {len(texts)} menu items...")
        embeddings = self.create_embeddings_batch(texts)
        
        if not embeddings:
            logger.error("Failed to create embeddings")
            return 0
        
        # Insert into database
        for i, (item_data, embedding) in enumerate(zip(items_data, embeddings)):
            try:
                item_data['embedding'] = embedding
                
                # Upsert
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

# Global instance
lightweight_embedding_service = LightweightEmbeddingService()