#!/usr/bin/env python3
"""
Generate simple embeddings for legal services
Using a basic approach that creates searchable vectors
"""
import json
import random
import hashlib
from sqlalchemy import text
from database import SessionLocal

def create_simple_embedding(text: str, dim: int = 384):
    """Create a deterministic pseudo-embedding based on text content"""
    # Use hash to ensure same text always gets same embedding
    hash_obj = hashlib.sha256(text.encode())
    seed = int(hash_obj.hexdigest()[:8], 16)
    random.seed(seed)
    
    # Create vector with some structure
    embedding = []
    words = text.lower().split()
    
    # Base embedding from hash
    for i in range(dim):
        # Mix word features into embedding
        if i < len(words):
            word_val = sum(ord(c) for c in words[i]) / 1000.0
        else:
            word_val = 0
        
        base_val = random.gauss(0, 0.3)
        embedding.append(base_val + word_val * 0.1)
    
    # Normalize
    magnitude = sum(x**2 for x in embedding) ** 0.5
    if magnitude > 0:
        embedding = [x / magnitude for x in embedding]
    
    return embedding

def main():
    """Generate embeddings for legal services"""
    db = SessionLocal()
    
    try:
        # Get legal business products
        query = text("""
            SELECT p.id, p.name, p.description, p.price, p.category, 
                   p.product_type, p.duration, p.requirements::text, p.features::text
            FROM products p
            JOIN businesses b ON p.business_id = b.business_id
            WHERE b.business_type = 'legal_visa'
            AND (p.combined_embedding IS NULL OR p.name_embedding IS NULL)
        """)
        
        products = db.execute(query).fetchall()
        print(f"Found {len(products)} legal products without embeddings")
        
        for product in products:
            print(f"\nProcessing: {product[1]}")
            
            # Create searchable text
            parts = [
                f"Name: {product[1]}",
                f"Description: {product[2]}",
                f"Price: ${product[3]}",
                f"Category: {product[4]}"
            ]
            
            if product[6]:  # duration
                parts.append(f"Duration: {product[6]}")
            
            if product[7]:  # requirements
                try:
                    req = json.loads(product[7])
                    if isinstance(req, dict):
                        if 'documents' in req:
                            parts.append(f"Documents: {', '.join(req['documents'])}")
                        if 'eligibility' in req:
                            parts.append(f"Eligibility: {', '.join(req['eligibility'])}")
                except:
                    pass
            
            if product[8]:  # features
                try:
                    features = json.loads(product[8])
                    if isinstance(features, list):
                        parts.append(f"Features: {', '.join(features)}")
                except:
                    pass
            
            combined_text = " | ".join(parts)
            
            # Create embeddings
            name_embedding = create_simple_embedding(product[1])
            desc_embedding = create_simple_embedding(product[2]) if product[2] else name_embedding
            combined_embedding = create_simple_embedding(combined_text)
            
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
                "name_emb": json.dumps(name_embedding),
                "desc_emb": json.dumps(desc_embedding),
                "combined_emb": json.dumps(combined_embedding)
            })
            
            print(f"  ✅ Created embeddings")
        
        db.commit()
        print(f"\n✅ Successfully created embeddings for {len(products)} products")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
        import traceback
        traceback.print_exc()
    finally:
        db.close()

if __name__ == "__main__":
    main()