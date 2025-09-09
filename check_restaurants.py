#!/usr/bin/env python3
"""Check available restaurants"""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway')
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def check_restaurants():
    """List all restaurants in database"""
    session = Session()
    try:
        result = session.execute("SELECT restaurant_id, rag_mode FROM restaurants LIMIT 10")
        restaurants = result.fetchall()
        
        print("Available restaurants:")
        for r in restaurants:
            print(f"  ID: {r[0]}, RAG Mode: {r[1]}")
            
        if not restaurants:
            print("  No restaurants found!")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_restaurants()