#!/usr/bin/env python3
"""
Index menu items locally (run on server)
"""
from sqlalchemy.orm import Session
from database import get_db, engine
from services.embedding_service import embedding_service
import models
import sys

def index_restaurant(restaurant_id: str):
    """Index a restaurant's menu items"""
    print(f"🍽️  Indexing menu for: {restaurant_id}")
    
    # Get database session
    db = next(get_db())
    
    try:
        # Get restaurant
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == restaurant_id
        ).first()
        
        if not restaurant:
            print(f"❌ Restaurant not found: {restaurant_id}")
            return False
        
        # Get menu items
        data = restaurant.data or {}
        menu_items = data.get("menu", [])
        
        if not menu_items:
            print("❌ No menu items found")
            return False
        
        print(f"📋 Found {len(menu_items)} menu items")
        
        # Index items
        indexed = embedding_service.index_restaurant_menu(
            db, 
            restaurant_id, 
            menu_items
        )
        
        print(f"✅ Successfully indexed {indexed} items")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False
    finally:
        db.close()

def main():
    """Main function"""
    restaurant_id = sys.argv[1] if len(sys.argv) > 1 else "bella_vista_restaurant"
    
    print("🚀 Menu Indexing Script")
    print("=" * 50)
    
    # Check if pgvector is ready
    from check_pgvector import check_pgvector
    if not check_pgvector():
        print("\n❌ Please fix pgvector setup first")
        return
    
    # Index the restaurant
    if index_restaurant(restaurant_id):
        print("\n✅ Indexing complete!")
        print("RAG is now active for this restaurant")
    else:
        print("\n❌ Indexing failed")

if __name__ == "__main__":
    main()