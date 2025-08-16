"""
Simple admin endpoints that work
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import get_current_owner
import models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/simple-admin", tags=["simple-admin"])

@router.delete("/delete/{restaurant_id}")
def simple_delete_restaurant(
    restaurant_id: str,
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Simple delete endpoint for admin.
    """
    # Check if admin
    if current_admin.restaurant_id != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Don't delete self
    if restaurant_id == "admin@admin.com":
        raise HTTPException(status_code=400, detail="Cannot delete admin")
    
    try:
        # Get restaurant info first
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == restaurant_id
        ).first()
        
        if not restaurant:
            return {"success": False, "message": f"Restaurant {restaurant_id} not found"}
        
        # Comprehensive deletion in correct order for all foreign keys
        # 1. Delete embeddings
        deleted_embeddings = db.execute(text("DELETE FROM menu_embeddings WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        
        # 2. Delete chat messages
        deleted_messages = db.execute(text("DELETE FROM chat_messages WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        
        # 3. Delete chat_logs (must be before clients due to foreign key)
        deleted_logs = db.execute(text("""
            DELETE FROM chat_logs 
            WHERE client_id IN (
                SELECT id FROM clients WHERE restaurant_id = :rid
            )
        """), {"rid": restaurant_id})
        
        # 4. Delete clients
        deleted_clients = db.execute(text("DELETE FROM clients WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        
        # 5. Finally delete the restaurant
        db.delete(restaurant)
        
        # Commit all changes
        db.commit()
        
        return {
            "success": True, 
            "message": f"Deleted {restaurant_id}",
            "deleted_counts": {
                "embeddings": deleted_embeddings.rowcount,
                "messages": deleted_messages.rowcount,
                "logs": deleted_logs.rowcount,
                "clients": deleted_clients.rowcount
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Delete error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/list-all")
def simple_list_all(
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Simple list all restaurants.
    """
    if current_admin.restaurant_id != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Admin only")
    
    restaurants = db.query(models.Restaurant).all()
    return [
        {
            "restaurant_id": r.restaurant_id,
            "name": r.data.get("name", "Unknown") if r.data else "Unknown",
            "role": r.role,
            "menu_count": len(r.data.get("menu", [])) if r.data else 0
        }
        for r in restaurants
    ]