"""
Admin management endpoints for system administration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import get_current_owner
import models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin", tags=["admin"])

@router.delete("/restaurant/{restaurant_id}")
def admin_delete_restaurant(
    restaurant_id: str,
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Delete any restaurant (admin only).
    Only admin@admin.com can use this endpoint.
    """
    # Ensure it's the admin account
    if current_admin.restaurant_id not in ["admin", "admin@admin.com"]:
        raise HTTPException(status_code=403, detail="Only system admin can delete restaurants")
    
    # Prevent deleting self
    if restaurant_id in ["admin", "admin@admin.com"]:
        raise HTTPException(status_code=400, detail="Cannot delete admin account")
    
    # Find the restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    try:
        # Delete embeddings first
        deleted_embeddings = db.execute(text("""
            DELETE FROM menu_embeddings 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id})
        
        # Delete chat messages
        deleted_messages = db.execute(text("""
            DELETE FROM chat_messages 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id})
        
        # Delete clients
        deleted_clients = db.execute(text("""
            DELETE FROM clients 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id})
        
        # Delete the restaurant
        db.delete(restaurant)
        db.commit()
        
        logger.info(f"Admin deleted restaurant {restaurant_id}")
        
        return {
            "message": f"Restaurant {restaurant_id} deleted successfully",
            "deleted": {
                "embeddings": deleted_embeddings.rowcount,
                "messages": deleted_messages.rowcount,
                "clients": deleted_clients.rowcount
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete restaurant {restaurant_id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/restaurants")
def get_all_restaurants(
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get all restaurants (admin only).
    """
    if current_admin.restaurant_id != "admin":
        raise HTTPException(status_code=403, detail="Only admin can view all restaurants")
    
    restaurants = db.query(models.Restaurant).all()
    
    # Format the response
    result = []
    for restaurant in restaurants:
        data = restaurant.data or {}
        result.append({
            "restaurant_id": restaurant.restaurant_id,
            "name": data.get("name", restaurant.restaurant_id),
            "role": restaurant.role,
            "business_type": data.get("business_type", "restaurant")
        })
    
    return result

@router.get("/restaurants/summary")
def get_restaurants_summary(
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get summary of all restaurants (admin only).
    """
    if current_admin.restaurant_id not in ["admin", "admin@admin.com"]:
        raise HTTPException(status_code=403, detail="Only system admin can view summary")
    
    # Get restaurant statistics
    stats = db.execute(text("""
        SELECT 
            r.restaurant_id,
            r.data->>'name' as name,
            r.role,
            COALESCE(jsonb_array_length(r.data->'menu'), 0) as menu_count,
            COUNT(DISTINCT e.id) as embedding_count,
            COUNT(DISTINCT c.client_id) as client_count,
            COUNT(DISTINCT m.id) as message_count,
            r.created_at
        FROM restaurants r
        LEFT JOIN menu_embeddings e ON r.restaurant_id = e.restaurant_id
        LEFT JOIN clients c ON r.restaurant_id = c.restaurant_id
        LEFT JOIN chat_messages m ON r.restaurant_id = m.restaurant_id
        GROUP BY r.restaurant_id, r.data, r.role, r.created_at
        ORDER BY r.created_at DESC
    """)).fetchall()
    
    results = []
    for row in stats:
        results.append({
            "restaurant_id": row.restaurant_id,
            "name": row.name or "Unknown",
            "role": row.role,
            "menu_items": row.menu_count,
            "embeddings": row.embedding_count,
            "clients": row.client_count,
            "messages": row.message_count,
            "created_at": row.created_at.isoformat() if row.created_at else None,
            "is_dummy": row.menu_count == 0 or (row.menu_count == 1 and row.embedding_count == 0)
        })
    
    return {
        "total_restaurants": len(results),
        "restaurants": results
    }