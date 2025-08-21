#!/usr/bin/env python3
"""
Generate embeddings directly using OpenAI API
For when the local embedding service isn't available
"""
import os
import json
import openai
from sqlalchemy import text
from database import SessionLocal

# Use OpenAI API for embeddings
openai.api_key = os.getenv("OPENAI_API_KEY")

def create_embedding(text: str):
    """Create embedding using OpenAI"""
    try:
        response = openai.Embedding.create(
            model="text-embedding-ada-002",
            input=text
        )
        return response['data'][0]['embedding']
    except Exception as e:
        print(f"Error creating embedding: {e}")
        return None

def create_product_text(product: dict, business_type: str) -> str:
    """Create searchable text from product"""
    parts = []
    
    # Universal fields
    parts.append(f"Name: {product['name']}")
    parts.append(f"Description: {product['description']}")
    parts.append(f"Category: {product['category']}")
    parts.append(f"Price: ${product['price']}")
    
    # Service-specific fields
    if product.get('duration'):
        parts.append(f"Processing Time: {product['duration']}")
    
    if product.get('requirements') and isinstance(product['requirements'], dict):
        if 'documents' in product['requirements']:
            parts.append(f"Required Documents: {', '.join(product['requirements']['documents'])}")
        if 'eligibility' in product['requirements']:
            parts.append(f"Eligibility: {', '.join(product['requirements']['eligibility'])}")
    
    if product.get('features') and isinstance(product['features'], list):
        parts.append(f"Includes: {', '.join(product['features'])}")
    
    if product.get('tags') and isinstance(product['tags'], list):
        parts.append(f"Tags: {', '.join(product['tags'])}")
    
    return " | ".join(parts)

def main():
    """Generate embeddings for all products without them"""
    db = SessionLocal()
    
    try:
        # Get all products without embeddings
        query = text("""
            SELECT id, business_id, name, description, price, category, 
                   product_type, duration, requirements::text, features::text, tags::text
            FROM products 
            WHERE combined_embedding IS NULL
            OR name_embedding IS NULL
        """)
        
        products = db.execute(query).fetchall()
        print(f"Found {len(products)} products without embeddings")
        
        for product in products:
            print(f"\nProcessing: {product[2]} ({product[0]})")
            
            # Convert to dict
            product_dict = {
                "id": product[0],
                "business_id": product[1],
                "name": product[2],
                "description": product[3],
                "price": product[4],
                "category": product[5],
                "product_type": product[6],
                "duration": product[7],
                "requirements": json.loads(product[8]) if product[8] else {},
                "features": json.loads(product[9]) if product[9] else [],
                "tags": json.loads(product[10]) if product[10] else []
            }
            
            # Get business type
            business_query = text("""
                SELECT business_type FROM businesses 
                WHERE business_id = :business_id
            """)
            result = db.execute(business_query, {"business_id": product_dict["business_id"]}).fetchone()
            business_type = result[0] if result else "restaurant"
            
            # Create embeddings
            print(f"  Creating embeddings for {business_type} product...")
            
            # Name embedding
            name_embedding = create_embedding(product_dict["name"])
            
            # Description embedding
            desc_embedding = create_embedding(product_dict["description"]) if product_dict["description"] else None
            
            # Combined text embedding
            combined_text = create_product_text(product_dict, business_type)
            combined_embedding = create_embedding(combined_text)
            
            # Update database
            if name_embedding and combined_embedding:
                update_query = text("""
                    UPDATE products 
                    SET name_embedding = :name_emb::jsonb,
                        description_embedding = :desc_emb::jsonb,
                        combined_embedding = :combined_emb::jsonb
                    WHERE id = :id
                """)
                
                db.execute(update_query, {
                    "id": product_dict["id"],
                    "name_emb": json.dumps(name_embedding),
                    "desc_emb": json.dumps(desc_embedding) if desc_embedding else None,
                    "combined_emb": json.dumps(combined_embedding)
                })
                
                print(f"  ✅ Updated embeddings")
            else:
                print(f"  ❌ Failed to create embeddings")
        
        db.commit()
        print(f"\n✅ Successfully updated embeddings for {len(products)} products")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    main()