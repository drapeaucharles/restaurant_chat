"""
OpenAI Embedding Service
Uses OpenAI API for embeddings since ML libraries are too large for Railway
This runs on the centralized Railway server, not on GPUs
"""
import os
import openai
import logging
from typing import List, Optional
import json
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

# Use OpenAI API
openai.api_key = os.getenv("OPENAI_API_KEY")

class OpenAIEmbeddingService:
    """Embedding service using OpenAI API"""
    
    def __init__(self):
        self.model = "text-embedding-ada-002"
        self.embedding_dim = 1536  # OpenAI embedding dimension
        
    def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding using OpenAI API"""
        if not openai.api_key:
            logger.error("OpenAI API key not set")
            return None
            
        try:
            response = openai.Embedding.create(
                model=self.model,
                input=text
            )
            return response['data'][0]['embedding']
        except Exception as e:
            logger.error(f"OpenAI embedding failed: {e}")
            return None
    
    def create_batch_embeddings(self, texts: List[str]) -> Optional[List[List[float]]]:
        """Create embeddings for multiple texts"""
        if not openai.api_key:
            logger.error("OpenAI API key not set")
            return None
            
        try:
            response = openai.Embedding.create(
                model=self.model,
                input=texts
            )
            return [item['embedding'] for item in response['data']]
        except Exception as e:
            logger.error(f"OpenAI batch embedding failed: {e}")
            return None
    
    def update_product_embeddings(self, db: Session, business_id: str):
        """Update embeddings for all products of a business"""
        try:
            # Get products without embeddings
            query = text("""
                SELECT id, name, description, price, category, 
                       product_type, duration, features::text, tags::text
                FROM products 
                WHERE business_id = :business_id
                AND (combined_embedding IS NULL 
                     OR jsonb_array_length(combined_embedding) != 1536)
            """)
            
            products = db.execute(query, {"business_id": business_id}).fetchall()
            
            if not products:
                logger.info(f"All products already have embeddings for {business_id}")
                return
            
            logger.info(f"Updating embeddings for {len(products)} products")
            
            for product in products:
                # Create searchable text
                parts = [f"Name: {product[1]}"]
                if product[2]:  # description
                    parts.append(f"Description: {product[2]}")
                if product[4]:  # category
                    parts.append(f"Category: {product[4]}")
                if product[5]:  # product_type
                    parts.append(f"Type: {product[5]}")
                if product[6]:  # duration
                    parts.append(f"Duration: {product[6]}")
                if product[7]:  # features
                    try:
                        features = json.loads(product[7])
                        if features:
                            parts.append(f"Features: {', '.join(features)}")
                    except:
                        pass
                if product[8]:  # tags
                    try:
                        tags = json.loads(product[8])
                        if tags:
                            parts.append(f"Tags: {', '.join(tags)}")
                    except:
                        pass
                
                combined_text = " | ".join(parts)
                
                # Create embeddings
                name_embedding = self.create_embedding(product[1])
                desc_embedding = self.create_embedding(product[2]) if product[2] else None
                combined_embedding = self.create_embedding(combined_text)
                
                if combined_embedding:
                    # Update database
                    update_query = text("""
                        UPDATE products 
                        SET name_embedding = :name_emb::jsonb,
                            description_embedding = :desc_emb::jsonb,
                            combined_embedding = :combined_emb::jsonb
                        WHERE id = :id
                    """)
                    
                    db.execute(update_query, {
                        "id": product[0],
                        "name_emb": json.dumps(name_embedding) if name_embedding else None,
                        "desc_emb": json.dumps(desc_embedding) if desc_embedding else None,
                        "combined_emb": json.dumps(combined_embedding)
                    })
                    
                    logger.info(f"Updated embeddings for: {product[1]}")
            
            db.commit()
            logger.info(f"Successfully updated embeddings for {business_id}")
            
        except Exception as e:
            logger.error(f"Failed to update embeddings: {e}")
            db.rollback()

# Singleton instance
openai_embedding_service = OpenAIEmbeddingService()