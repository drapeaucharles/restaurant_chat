"""
Admin endpoints for managing embeddings
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_owner
import models
from services.embedding_service import embedding_service
from sqlalchemy import text
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embeddings/admin", tags=["embeddings-admin"])

@router.post("/initialize/{restaurant_id}")
def initialize_restaurant_embeddings(
    restaurant_id: str,
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Initialize embeddings for a restaurant that doesn't have them yet.
    Admin or restaurant owner only.
    """
    # Check permissions
    if current_owner.restaurant_id != restaurant_id and current_owner.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Check current status
    existing = db.execute(text("""
        SELECT COUNT(*) as count 
        FROM menu_embeddings 
        WHERE restaurant_id = :restaurant_id
    """), {'restaurant_id': restaurant_id}).fetchone()
    
    if existing and existing.count > 0:
        return {
            "message": "Restaurant already has embeddings",
            "restaurant_id": restaurant_id,
            "existing_count": existing.count
        }
    
    # Get menu items
    menu_items = restaurant.data.get("menu", []) if restaurant.data else []
    
    if not menu_items:
        return {
            "message": "No menu items to index",
            "restaurant_id": restaurant_id
        }
    
    # Create embeddings
    try:
        indexed_count = embedding_service.index_restaurant_menu(
            db=db,
            restaurant_id=restaurant_id,
            menu_items=menu_items
        )
        db.commit()
        
        return {
            "message": "Embeddings initialized successfully",
            "restaurant_id": restaurant_id,
            "indexed": indexed_count,
            "menu_count": len(menu_items)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to initialize embeddings for {restaurant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/initialize-all")
def initialize_all_restaurants(
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Initialize embeddings for all restaurants without them.
    Admin only endpoint.
    """
    # Check if admin (you might want to implement proper admin check)
    if current_owner.restaurant_id != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Find restaurants without embeddings
    restaurants_without_embeddings = db.execute(text("""
        SELECT r.restaurant_id, r.data
        FROM restaurants r
        LEFT JOIN (
            SELECT restaurant_id, COUNT(*) as count 
            FROM menu_embeddings 
            GROUP BY restaurant_id
        ) e ON r.restaurant_id = e.restaurant_id
        WHERE e.count IS NULL OR e.count = 0
    """)).fetchall()
    
    results = []
    total_indexed = 0
    
    for restaurant in restaurants_without_embeddings:
        restaurant_id = restaurant.restaurant_id
        data = restaurant.data or {}
        menu_items = data.get("menu", [])
        
        if menu_items:
            try:
                indexed = embedding_service.index_restaurant_menu(
                    db=db,
                    restaurant_id=restaurant_id,
                    menu_items=menu_items
                )
                db.commit()
                
                results.append({
                    "restaurant_id": restaurant_id,
                    "status": "success",
                    "indexed": indexed
                })
                total_indexed += indexed
            except Exception as e:
                db.rollback()
                results.append({
                    "restaurant_id": restaurant_id,
                    "status": "failed",
                    "error": str(e)
                })
        else:
            results.append({
                "restaurant_id": restaurant_id,
                "status": "skipped",
                "reason": "no menu items"
            })
    
    return {
        "message": "Batch initialization complete",
        "total_restaurants": len(restaurants_without_embeddings),
        "total_indexed": total_indexed,
        "results": results
    }

@router.get("/status")
def get_embedding_status(
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get embedding status for all restaurants.
    Admin only endpoint.
    """
    # Check if admin
    if current_owner.restaurant_id != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get status for all restaurants
    status = db.execute(text("""
        SELECT 
            r.restaurant_id,
            r.data->>'name' as restaurant_name,
            COALESCE(jsonb_array_length(r.data->'menu'), 0) as menu_count,
            COUNT(e.id) as embedding_count
        FROM restaurants r
        LEFT JOIN menu_embeddings e ON r.restaurant_id = e.restaurant_id
        GROUP BY r.restaurant_id, r.data
        ORDER BY r.restaurant_id
    """)).fetchall()
    
    results = []
    for row in status:
        results.append({
            "restaurant_id": row.restaurant_id,
            "restaurant_name": row.restaurant_name,
            "menu_count": row.menu_count,
            "embedding_count": row.embedding_count,
            "fully_indexed": row.menu_count == row.embedding_count,
            "sync_needed": row.menu_count != row.embedding_count
        })
    
    # Summary stats
    total_restaurants = len(results)
    fully_indexed = sum(1 for r in results if r["fully_indexed"])
    needs_sync = sum(1 for r in results if r["sync_needed"])
    
    return {
        "summary": {
            "total_restaurants": total_restaurants,
            "fully_indexed": fully_indexed,
            "needs_sync": needs_sync,
            "percentage_indexed": round((fully_indexed / total_restaurants * 100), 2) if total_restaurants > 0 else 0
        },
        "restaurants": results
    }

@router.post("/rebuild/{restaurant_id}")
def rebuild_restaurant_embeddings(
    restaurant_id: str,
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Rebuild all embeddings for a restaurant (delete and recreate).
    Useful if embeddings are corrupted or need updating.
    """
    # Check permissions
    if current_owner.restaurant_id != restaurant_id and current_owner.role != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    menu_items = restaurant.data.get("menu", []) if restaurant.data else []
    
    if not menu_items:
        return {
            "message": "No menu items to index",
            "restaurant_id": restaurant_id
        }
    
    try:
        # Delete existing embeddings
        deleted = db.execute(text("""
            DELETE FROM menu_embeddings 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id})
        
        # Create new embeddings
        indexed_count = embedding_service.index_restaurant_menu(
            db=db,
            restaurant_id=restaurant_id,
            menu_items=menu_items
        )
        db.commit()
        
        return {
            "message": "Embeddings rebuilt successfully",
            "restaurant_id": restaurant_id,
            "deleted": deleted.rowcount,
            "indexed": indexed_count,
            "menu_count": len(menu_items)
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to rebuild embeddings for {restaurant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))