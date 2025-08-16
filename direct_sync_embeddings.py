#!/usr/bin/env python3
"""
Direct database sync for embeddings
This syncs embeddings directly in the database
"""
import os
import sys
sys.path.append('/home/charles-drapeau/Documents/Project/Restaurant/BackEnd')

from database import SessionLocal
from services.embedding_service import embedding_service
from sqlalchemy import text
import models
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def sync_embeddings_directly():
    """Sync embeddings directly in the database"""
    print("🔄 DIRECT EMBEDDING SYNC")
    print("=" * 60)
    
    db = SessionLocal()
    
    try:
        # Get restaurants that need sync
        restaurants_needing_sync = db.execute(text("""
            SELECT 
                r.restaurant_id,
                r.data->>'name' as name,
                r.data,
                COALESCE(jsonb_array_length(r.data->'menu'), 0) as menu_count,
                COUNT(e.id) as embedding_count
            FROM restaurants r
            LEFT JOIN menu_embeddings e ON r.restaurant_id = e.restaurant_id
            WHERE r.role = 'owner'
            GROUP BY r.restaurant_id, r.data
            HAVING COALESCE(jsonb_array_length(r.data->'menu'), 0) != COUNT(e.id)
            AND COALESCE(jsonb_array_length(r.data->'menu'), 0) > 0
        """)).fetchall()
        
        print(f"Found {len(restaurants_needing_sync)} restaurants needing sync\n")
        
        total_created = 0
        
        for row in restaurants_needing_sync:
            restaurant_id = row.restaurant_id
            name = row.name or restaurant_id
            menu_count = row.menu_count
            current_embeddings = row.embedding_count
            
            print(f"📍 {name} ({restaurant_id})")
            print(f"   Current: {current_embeddings} embeddings, Need: {menu_count}")
            
            # Get menu items from data
            data = row.data or {}
            menu_items = data.get('menu', [])
            
            if menu_items:
                try:
                    # Clear existing embeddings
                    deleted = db.execute(text("""
                        DELETE FROM menu_embeddings 
                        WHERE restaurant_id = :restaurant_id
                    """), {'restaurant_id': restaurant_id})
                    
                    print(f"   Cleared {deleted.rowcount} old embeddings")
                    
                    # Create new embeddings
                    indexed = embedding_service.index_restaurant_menu(
                        db=db,
                        restaurant_id=restaurant_id,
                        menu_items=menu_items
                    )
                    db.commit()
                    
                    print(f"   ✅ Created {indexed} new embeddings")
                    total_created += indexed
                    
                except Exception as e:
                    print(f"   ❌ Error: {e}")
                    db.rollback()
                    logger.error(f"Failed to sync {restaurant_id}: {e}")
            
            print()
        
        # Final check
        print("=" * 60)
        print("📊 FINAL STATUS CHECK")
        print("=" * 60)
        
        final_status = db.execute(text("""
            SELECT 
                r.restaurant_id,
                r.data->>'name' as name,
                COALESCE(jsonb_array_length(r.data->'menu'), 0) as menu_count,
                COUNT(e.id) as embedding_count,
                CASE 
                    WHEN COALESCE(jsonb_array_length(r.data->'menu'), 0) = COUNT(e.id) 
                    THEN 'SYNCED'
                    ELSE 'NEEDS SYNC'
                END as status
            FROM restaurants r
            LEFT JOIN menu_embeddings e ON r.restaurant_id = e.restaurant_id
            WHERE r.role = 'owner'
            GROUP BY r.restaurant_id, r.data
            ORDER BY r.restaurant_id
        """)).fetchall()
        
        synced_count = 0
        for row in final_status:
            icon = "✅" if row.status == "SYNCED" else "⚠️"
            print(f"{icon} {row.name} ({row.restaurant_id}): {row.embedding_count}/{row.menu_count} embeddings")
            if row.status == "SYNCED":
                synced_count += 1
        
        print(f"\n✅ Sync complete! {synced_count}/{len(final_status)} restaurants fully synced")
        print(f"🔢 Total embeddings created: {total_created}")
        
    except Exception as e:
        print(f"❌ Critical error: {e}")
        logger.error(f"Sync failed: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    # Safety check
    db_url = os.getenv("DATABASE_URL", "")
    if "railway.app" in db_url or "production" in db_url:
        print("⚠️  WARNING: This will modify the production database!")
        print("Database:", db_url[:50] + "...")
        response = input("\nAre you SURE you want to sync production embeddings? (type 'yes' to confirm): ")
        if response.lower() != 'yes':
            print("Cancelled.")
            exit()
    
    sync_embeddings_directly()