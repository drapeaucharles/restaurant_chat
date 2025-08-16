#!/usr/bin/env python3
"""
Sync embeddings for all restaurants that need it
This would normally require admin authentication
"""
import os
import sys
sys.path.append('/home/charles-drapeau/Documents/Project/Restaurant/BackEnd')

from database import get_db
from services.embedding_service import embedding_service
from sqlalchemy import text
import models

def sync_all_restaurants():
    """Sync embeddings for all restaurants locally"""
    print("🔄 SYNCING EMBEDDINGS FOR ALL RESTAURANTS")
    print("=" * 60)
    
    db = next(get_db())
    
    try:
        # Get all restaurants
        restaurants = db.query(models.Restaurant).all()
        
        total_synced = 0
        total_created = 0
        
        for restaurant in restaurants:
            restaurant_id = restaurant.restaurant_id
            menu_items = restaurant.data.get("menu", []) if restaurant.data else []
            
            if not menu_items:
                print(f"⏭️  Skipping {restaurant_id} - no menu items")
                continue
            
            # Check current embeddings
            result = db.execute(text("""
                SELECT COUNT(*) as count 
                FROM menu_embeddings 
                WHERE restaurant_id = :restaurant_id
            """), {'restaurant_id': restaurant_id}).fetchone()
            
            current_count = result.count if result else 0
            
            if current_count != len(menu_items):
                print(f"\n🔧 Syncing {restaurant_id}")
                print(f"   Current embeddings: {current_count}")
                print(f"   Menu items: {len(menu_items)}")
                
                try:
                    # Clear existing
                    db.execute(text("""
                        DELETE FROM menu_embeddings 
                        WHERE restaurant_id = :restaurant_id
                    """), {'restaurant_id': restaurant_id})
                    
                    # Create new embeddings
                    indexed = embedding_service.index_restaurant_menu(
                        db=db,
                        restaurant_id=restaurant_id,
                        menu_items=menu_items
                    )
                    db.commit()
                    
                    print(f"   ✅ Created {indexed} embeddings")
                    total_synced += 1
                    total_created += indexed
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    db.rollback()
            else:
                print(f"✅ {restaurant_id} - already in sync ({current_count} embeddings)")
        
        print("\n" + "=" * 60)
        print(f"📊 SYNC COMPLETE")
        print(f"   Restaurants synced: {total_synced}")
        print(f"   Embeddings created: {total_created}")
        
    finally:
        db.close()

if __name__ == "__main__":
    # Check if we're in production
    if os.getenv("DATABASE_URL", "").startswith("postgresql://"):
        print("⚠️  This script modifies the database!")
        print("It should only be run with proper authorization.")
        print("\nTo sync in production, use the admin endpoints:")
        print("- POST /embeddings/admin/initialize-all")
        print("- POST /embeddings/admin/rebuild/{restaurant_id}")
        print("\nOr restaurant owners can update their menu via the frontend.")
    else:
        response = input("\nRun sync locally? (y/N): ")
        if response.lower() == 'y':
            sync_all_restaurants()
        else:
            print("Cancelled.")