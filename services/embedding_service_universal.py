"""
Universal embedding service for any business type
Works with restaurants, legal services, hotels, etc.
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

class UniversalEmbeddingService:
    """Universal service for creating and managing embeddings for any business"""
    
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
    
    def create_product_text(self, product: Dict, business_type: str = "restaurant") -> str:
        """Create searchable text from any product/service"""
        parts = []
        
        # Name and description (universal)
        if product.get("name"):
            parts.append(f"Name: {product['name']}")
        if product.get("description"):
            parts.append(f"Description: {product['description']}")
        if product.get("category"):
            parts.append(f"Category: {product['category']}")
        
        # Price (formatted based on business type)
        if product.get("price"):
            if business_type in ["legal_visa", "consulting", "service"]:
                parts.append(f"Price: ${product['price']} USD")
            else:
                parts.append(f"Price: ${product['price']}")
        
        # Business-specific fields
        if business_type == "restaurant":
            # Restaurant-specific
            if product.get("allergens"):
                parts.append(f"Allergens: {', '.join(product['allergens'])}")
            if product.get("dietary_info"):
                parts.append(f"Dietary: {', '.join(product['dietary_info'])}")
                
        elif business_type in ["legal_visa", "consulting"]:
            # Service-specific
            if product.get("duration"):
                parts.append(f"Processing Time: {product['duration']}")
            if product.get("requirements") and isinstance(product["requirements"], dict):
                if "documents" in product["requirements"]:
                    parts.append(f"Required Documents: {', '.join(product['requirements']['documents'])}")
                if "eligibility" in product["requirements"]:
                    parts.append(f"Eligibility: {', '.join(product['requirements']['eligibility'])}")
            if product.get("features"):
                parts.append(f"Includes: {', '.join(product['features'])}")
                
        elif business_type == "hotel":
            # Hotel-specific
            if product.get("room_type"):
                parts.append(f"Room Type: {product['room_type']}")
            if product.get("amenities"):
                parts.append(f"Amenities: {', '.join(product['amenities'])}")
            if product.get("capacity"):
                parts.append(f"Capacity: {product['capacity']} guests")
                
        elif business_type == "salon":
            # Salon-specific
            if product.get("duration"):
                parts.append(f"Duration: {product['duration']}")
            if product.get("stylist_level"):
                parts.append(f"Stylist Level: {product['stylist_level']}")
        
        # Universal tags
        if product.get("tags"):
            parts.append(f"Tags: {', '.join(product['tags'])}")
        
        # Custom attributes (catch-all for any business)
        if product.get("custom_attributes"):
            for key, value in product["custom_attributes"].items():
                parts.append(f"{key}: {value}")
        
        return " | ".join(parts)
    
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding from text"""
        if not self.model:
            return None
            
        try:
            embedding = self.model.encode(text)
            return embedding.tolist()
        except Exception as e:
            logger.error(f"Failed to create embedding: {e}")
            return None
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        if not ML_AVAILABLE:
            return 0.0
            
        try:
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            norm1 = np.linalg.norm(vec1)
            norm2 = np.linalg.norm(vec2)
            
            if norm1 == 0 or norm2 == 0:
                return 0.0
                
            similarity = dot_product / (norm1 * norm2)
            return float(similarity)
        except Exception as e:
            logger.error(f"Failed to calculate similarity: {e}")
            return 0.0
    
    def update_product_embeddings(self, db: Session, business_id: str, business_type: str = "restaurant"):
        """Update embeddings for all products of a business"""
        if not self.model:
            logger.warning("Model not available, skipping embedding update")
            return
        
        try:
            # Get business to determine type
            business_query = text("""
                SELECT business_type FROM businesses 
                WHERE business_id = :business_id
            """)
            result = db.execute(business_query, {"business_id": business_id}).fetchone()
            if result and result[0]:
                business_type = result[0]
            
            # Get all products
            query = text("""
                SELECT id, name, description, price, category, 
                       product_type, duration, requirements::text, features::text, tags::text
                FROM products 
                WHERE business_id = :business_id
            """)
            
            products = db.execute(query, {"business_id": business_id}).fetchall()
            
            for product in products:
                # Convert row to dict
                product_dict = {
                    "id": product[0],
                    "name": product[1],
                    "description": product[2],
                    "price": product[3],
                    "category": product[4],
                    "product_type": product[5],
                    "duration": product[6],
                    "requirements": json.loads(product[7]) if product[7] else None,
                    "features": json.loads(product[8]) if product[8] else None,
                    "tags": json.loads(product[9]) if product[9] else []
                }
                
                # Create combined text
                combined_text = self.create_product_text(product_dict, business_type)
                
                # Create embeddings
                name_embedding = self.create_embedding(product_dict["name"]) if product_dict["name"] else None
                desc_embedding = self.create_embedding(product_dict["description"]) if product_dict["description"] else None
                combined_embedding = self.create_embedding(combined_text)
                
                # Update in database
                update_query = text("""
                    UPDATE products 
                    SET name_embedding = :name_emb,
                        description_embedding = :desc_emb,
                        combined_embedding = :combined_emb
                    WHERE id = :id
                """)
                
                db.execute(update_query, {
                    "id": product_dict["id"],
                    "name_emb": json.dumps(name_embedding) if name_embedding else None,
                    "desc_emb": json.dumps(desc_embedding) if desc_embedding else None,
                    "combined_emb": json.dumps(combined_embedding) if combined_embedding else None
                })
            
            db.commit()
            logger.info(f"Updated embeddings for {len(products)} products in {business_id}")
            
        except Exception as e:
            logger.error(f"Failed to update embeddings: {e}")
            db.rollback()
    
    def search_similar_items(self, db: Session, business_id: str, query: str, 
                           limit: int = 5, threshold: float = 0.3) -> List[Dict]:
        """Search for similar products using embeddings"""
        if not self.model:
            # Fall back to text search when ML is not available
            from services.text_search_service import text_search_service
            return text_search_service.search_products(db, business_id, query, limit)
        
        try:
            # Get business type
            business_query = text("""
                SELECT business_type FROM businesses 
                WHERE business_id = :business_id
            """)
            result = db.execute(business_query, {"business_id": business_id}).fetchone()
            business_type = result[0] if result and result[0] else "restaurant"
            
            # Create query embedding
            query_embedding = self.create_embedding(query)
            if not query_embedding:
                return []
            
            # Get all products with embeddings
            products_query = text("""
                SELECT id, name, description, price, category, 
                       combined_embedding::text, product_type, 
                       duration, requirements::text, features::text
                FROM products 
                WHERE business_id = :business_id 
                AND combined_embedding IS NOT NULL
                AND available = true
            """)
            
            products = db.execute(products_query, {"business_id": business_id}).fetchall()
            
            # Calculate similarities
            results = []
            for product in products:
                try:
                    product_embedding = json.loads(product[5])
                    similarity = self.calculate_similarity(query_embedding, product_embedding)
                    
                    if similarity >= threshold:
                        result_dict = {
                            "id": product[0],
                            "name": product[1],
                            "description": product[2],
                            "price": product[3],
                            "category": product[4],
                            "similarity": similarity,
                            "product_type": product[6],
                            "duration": product[7]
                        }
                        
                        # Add business-specific fields
                        if business_type in ["legal_visa", "consulting"]:
                            if product[8]:  # requirements
                                result_dict["requirements"] = json.loads(product[8])
                            if product[9]:  # features
                                result_dict["features"] = json.loads(product[9])
                        
                        results.append(result_dict)
                except Exception as e:
                    logger.error(f"Error processing product {product[0]}: {e}")
                    continue
            
            # Sort by similarity and return top results
            results.sort(key=lambda x: x["similarity"], reverse=True)
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []
    
    # Backward compatibility methods
    def update_menu_embeddings(self, db: Session, restaurant_id: str):
        """Backward compatibility for restaurant systems"""
        return self.update_product_embeddings(db, restaurant_id, "restaurant")
    
    def create_menu_item_text(self, item: Dict) -> str:
        """Backward compatibility for restaurant systems"""
        return self.create_product_text(item, "restaurant")

# Create singleton instance
universal_embedding_service = UniversalEmbeddingService()

# Backward compatibility
embedding_service = universal_embedding_service  # Alias for existing code