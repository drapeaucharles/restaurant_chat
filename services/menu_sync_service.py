"""
Service to sync menu updates to RAG embeddings
Ensures both Pinecone and PostgreSQL embeddings stay in sync
"""
import logging
from typing import List, Dict
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.embedding_service import embedding_service

logger = logging.getLogger(__name__)

class MenuSyncService:
    """Synchronize menu updates across both embedding systems"""
    
    def sync_restaurant_menu(self, db: Session, restaurant_id: str, menu_items: List[Dict]) -> Dict:
        """
        Sync menu items to PostgreSQL embeddings when restaurant updates menu
        
        Args:
            db: Database session
            restaurant_id: Restaurant ID
            menu_items: List of menu items from restaurant data
            
        Returns:
            Dict with sync results
        """
        try:
            # Clear existing embeddings for this restaurant
            db.execute(text("""
                DELETE FROM menu_embeddings 
                WHERE restaurant_id = :restaurant_id
            """), {'restaurant_id': restaurant_id})
            
            # Index new menu items
            indexed_count = 0
            if menu_items:
                indexed_count = embedding_service.index_restaurant_menu(
                    db=db,
                    restaurant_id=restaurant_id,
                    menu_items=menu_items
                )
            
            db.commit()
            
            logger.info(f"Synced {indexed_count} menu items for restaurant {restaurant_id}")
            
            return {
                'success': True,
                'indexed': indexed_count,
                'restaurant_id': restaurant_id
            }
            
        except Exception as e:
            logger.error(f"Menu sync failed for {restaurant_id}: {e}")
            db.rollback()
            return {
                'success': False,
                'error': str(e),
                'restaurant_id': restaurant_id
            }
    
    def sync_all_restaurants(self, db: Session) -> Dict:
        """
        Sync all restaurants' menus to embeddings
        Useful for initial setup or recovery
        """
        try:
            # Get all restaurants with menus
            restaurants = db.execute(text("""
                SELECT restaurant_id, data
                FROM restaurants
                WHERE data IS NOT NULL
                AND data::jsonb ? 'menu'
            """)).fetchall()
            
            results = []
            total_indexed = 0
            
            for restaurant in restaurants:
                restaurant_id = restaurant.restaurant_id
                data = restaurant.data
                menu_items = data.get('menu', []) if data else []
                
                if menu_items:
                    result = self.sync_restaurant_menu(db, restaurant_id, menu_items)
                    results.append(result)
                    if result['success']:
                        total_indexed += result['indexed']
            
            return {
                'success': True,
                'restaurants_synced': len(results),
                'total_items_indexed': total_indexed,
                'results': results
            }
            
        except Exception as e:
            logger.error(f"Bulk menu sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def check_sync_status(self, db: Session, restaurant_id: str) -> Dict:
        """
        Check if a restaurant's menu is properly synced
        """
        try:
            # Get menu count from restaurant data
            restaurant = db.execute(text("""
                SELECT data->'menu' as menu
                FROM restaurants
                WHERE restaurant_id = :restaurant_id
            """), {'restaurant_id': restaurant_id}).fetchone()
            
            if not restaurant:
                return {'exists': False}
            
            menu_items = restaurant.menu if restaurant.menu else []
            menu_count = len(menu_items) if isinstance(menu_items, list) else 0
            
            # Get embedding count
            embedding_count = db.execute(text("""
                SELECT COUNT(*) 
                FROM menu_embeddings
                WHERE restaurant_id = :restaurant_id
            """), {'restaurant_id': restaurant_id}).scalar()
            
            return {
                'exists': True,
                'menu_items': menu_count,
                'embeddings': embedding_count,
                'synced': menu_count == embedding_count,
                'restaurant_id': restaurant_id
            }
            
        except Exception as e:
            logger.error(f"Sync status check failed for {restaurant_id}: {e}")
            return {
                'exists': False,
                'error': str(e)
            }

# Singleton instance
menu_sync_service = MenuSyncService()