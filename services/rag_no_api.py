"""
RAG implementation without any 3rd party APIs
Uses keyword extraction and smart matching instead of embeddings
"""
import logging
from typing import List, Dict, Set, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
import re
from collections import Counter

logger = logging.getLogger(__name__)

class NoAPIRAG:
    """RAG without external embeddings API"""
    
    def __init__(self):
        # Keyword categories for semantic understanding
        self.food_categories = {
            'pasta': ['pasta', 'spaghetti', 'penne', 'fettuccine', 'linguine', 'ravioli', 'gnocchi', 'lasagna', 'noodle'],
            'pizza': ['pizza', 'margherita', 'pepperoni', 'calzone'],
            'seafood': ['seafood', 'fish', 'salmon', 'shrimp', 'lobster', 'crab', 'scallop', 'mussel', 'oyster'],
            'meat': ['beef', 'steak', 'chicken', 'pork', 'lamb', 'meat', 'bacon', 'sausage'],
            'vegetarian': ['vegetarian', 'veggie', 'vegetable', 'plant-based', 'meatless'],
            'vegan': ['vegan', 'plant-based', 'dairy-free'],
            'healthy': ['healthy', 'light', 'fresh', 'salad', 'grilled', 'steamed', 'low-cal'],
            'comfort': ['comfort', 'hearty', 'rich', 'creamy', 'cheesy', 'fried'],
            'spicy': ['spicy', 'hot', 'chili', 'pepper', 'jalapeño', 'sriracha'],
            'dessert': ['dessert', 'sweet', 'cake', 'ice cream', 'chocolate', 'tiramisu']
        }
        
    def extract_keywords(self, text: str) -> Set[str]:
        """Extract meaningful keywords from text"""
        # Simple tokenization and cleaning
        text = text.lower()
        # Remove prices, numbers, special chars
        text = re.sub(r'\$[\d.]+', '', text)
        text = re.sub(r'[^\w\s]', ' ', text)
        
        # Split and filter
        words = text.split()
        # Remove common words
        stopwords = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'with', 'our', 'is', 'are'}
        keywords = {w for w in words if len(w) > 2 and w not in stopwords}
        
        return keywords
    
    def calculate_relevance(self, query_keywords: Set[str], item_keywords: Set[str]) -> float:
        """Calculate relevance score without embeddings"""
        if not query_keywords or not item_keywords:
            return 0.0
        
        # Direct keyword matches
        exact_matches = len(query_keywords & item_keywords)
        
        # Category matches
        category_score = 0
        for category, terms in self.food_categories.items():
            query_in_category = any(q in terms for q in query_keywords)
            item_in_category = any(i in terms for i in item_keywords)
            if query_in_category and item_in_category:
                category_score += 0.3
        
        # Calculate final score
        total_keywords = len(query_keywords)
        base_score = exact_matches / total_keywords if total_keywords > 0 else 0
        final_score = min(base_score + category_score, 1.0)
        
        return final_score
    
    def search_items(self, db: Session, restaurant_id: str, query: str, limit: int = 5) -> List[Dict]:
        """Search items without using embeddings API"""
        
        # Extract query keywords
        query_keywords = self.extract_keywords(query)
        
        # Get all items from database
        items = db.execute(text("""
            SELECT item_id, item_name, item_description, item_price, 
                   item_category, item_ingredients, dietary_tags, full_text
            FROM menu_embeddings
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id}).fetchall()
        
        # Score each item
        scored_items = []
        for item in items:
            # Combine all text fields
            item_text = f"{item.item_name} {item.item_description or ''} {item.item_category or ''}"
            if item.full_text:
                item_text += f" {item.full_text}"
            
            item_keywords = self.extract_keywords(item_text)
            
            # Calculate relevance
            score = self.calculate_relevance(query_keywords, item_keywords)
            
            if score > 0.1:  # Threshold
                scored_items.append({
                    'item_id': item.item_id,
                    'name': item.item_name,
                    'description': item.item_description,
                    'price': item.item_price,
                    'category': item.item_category,
                    'ingredients': item.item_ingredients or [],
                    'dietary_tags': item.dietary_tags or [],
                    'similarity': score
                })
        
        # Sort by score and return top items
        scored_items.sort(key=lambda x: x['similarity'], reverse=True)
        return scored_items[:limit]
    
    def index_item(self, db: Session, restaurant_id: str, item: Dict) -> bool:
        """Index item without using embeddings API"""
        try:
            # Create searchable text
            full_text = f"{item.get('dish', '')} {item.get('description', '')} "
            full_text += f"{item.get('subcategory', '')} {' '.join(item.get('ingredients', []))}"
            
            # Extract keywords for faster searching
            keywords = self.extract_keywords(full_text)
            
            # Store in database (no embedding needed)
            db.execute(text("""
                INSERT INTO menu_embeddings 
                (restaurant_id, item_id, item_name, item_description, item_price,
                 item_category, item_ingredients, dietary_tags, full_text, embedding_json)
                VALUES 
                (:restaurant_id, :item_id, :item_name, :item_description, :item_price,
                 :item_category, :item_ingredients, :dietary_tags, :full_text, :keywords)
                ON CONFLICT (restaurant_id, item_id) DO UPDATE SET
                    item_name = EXCLUDED.item_name,
                    item_description = EXCLUDED.item_description,
                    full_text = EXCLUDED.full_text,
                    embedding_json = EXCLUDED.embedding_json,
                    updated_at = CURRENT_TIMESTAMP
            """), {
                'restaurant_id': restaurant_id,
                'item_id': str(item.get('id', item.get('dish', ''))),
                'item_name': item.get('dish', ''),
                'item_description': item.get('description', ''),
                'item_price': item.get('price', ''),
                'item_category': item.get('subcategory', ''),
                'item_ingredients': str(item.get('ingredients', [])),
                'dietary_tags': str([]),
                'full_text': full_text,
                'keywords': str(list(keywords))  # Store keywords instead of embeddings
            })
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to index item: {e}")
            return False

# Singleton instance
no_api_rag = NoAPIRAG()