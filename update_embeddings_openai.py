#!/usr/bin/env python3
"""
Update embeddings using OpenAI API
This runs on Railway server, not on decentralized GPUs
"""
import os
from sqlalchemy.orm import Session
from database import SessionLocal
from services.openai_embedding_service import openai_embedding_service

def main():
    """Update embeddings for all businesses"""
    db = SessionLocal()
    
    try:
        # Get all businesses
        from sqlalchemy import text
        businesses = db.execute(text("""
            SELECT business_id, business_type 
            FROM businesses
        """)).fetchall()
        
        print(f"Found {len(businesses)} businesses")
        
        for business_id, business_type in businesses:
            print(f"\nUpdating embeddings for {business_id} ({business_type})")
            openai_embedding_service.update_product_embeddings(db, business_id)
        
        print("\n✅ All embeddings updated!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()