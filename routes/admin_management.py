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
    if current_admin.restaurant_id not in ["admin", "admin@admin.com"]:
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

@router.get("/restaurant/{restaurant_id}")
def get_restaurant_details(
    restaurant_id: str,
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Get details of a specific restaurant (admin only).
    """
    if current_admin.restaurant_id not in ["admin", "admin@admin.com"]:
        raise HTTPException(status_code=403, detail="Only admin can view restaurant details")
    
    logger.info(f"Admin {current_admin.restaurant_id} fetching details for restaurant: {restaurant_id}")
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        logger.warning(f"Restaurant {restaurant_id} not found for admin access")
        raise HTTPException(status_code=404, detail=f"Restaurant '{restaurant_id}' not found")
    
    # Debug log to check data structure
    if restaurant.data:
        logger.info(f"Restaurant data has {len(restaurant.data)} keys")
        if 'name' in restaurant.data:
            logger.info(f"Restaurant name from DB: {restaurant.data.get('name')}")
        if 'restaurant_data' in restaurant.data:
            logger.warning(f"Found nested restaurant_data - this is likely a data corruption issue!")
    
    # Return restaurant data in a format compatible with the frontend
    data = restaurant.data or {}
    return {
        "restaurant_id": restaurant.restaurant_id,
        "name": data.get("name", restaurant.restaurant_id),
        "role": restaurant.role,
        "data": data,
        # Include all fields from data at the top level for compatibility
        **data
    }

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

@router.put("/restaurant/{restaurant_id}")
def update_restaurant_admin(
    restaurant_id: str,
    update_data: dict,
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Update any restaurant (admin only).
    """
    if current_admin.restaurant_id not in ["admin", "admin@admin.com"]:
        raise HTTPException(status_code=403, detail="Only admin can update any restaurant")
    
    logger.info(f"Admin {current_admin.restaurant_id} updating restaurant: {restaurant_id}")
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        logger.warning(f"Restaurant {restaurant_id} not found for admin update")
        raise HTTPException(status_code=404, detail=f"Restaurant '{restaurant_id}' not found")
    
    # Extract restaurant_data from the update payload
    if "restaurant_data" in update_data:
        new_data = update_data["restaurant_data"]
    else:
        new_data = update_data
    
    # Debug logging
    logger.info(f"Update payload received: {list(update_data.keys())}")
    logger.info(f"Extracted data keys: {list(new_data.keys()) if isinstance(new_data, dict) else 'not a dict'}")
    
    # Update restaurant data
    current_data = restaurant.data or {}
    logger.info(f"Current data has {len(current_data)} keys: {list(current_data.keys())[:5]}...")
    current_data.update(new_data)
    restaurant.data = current_data
    
    # Verify the update
    logger.info(f"Updated data has {len(restaurant.data)} keys")
    if 'menu' in restaurant.data:
        logger.info(f"Menu has {len(restaurant.data['menu'])} items")
    if 'name' in restaurant.data:
        logger.info(f"Restaurant name is now: {restaurant.data['name']}")
    
    db.commit()
    db.refresh(restaurant)
    
    logger.info(f"Restaurant {restaurant_id} updated successfully by admin")
    
    # Return consistent response format
    return {
        "restaurant_id": restaurant.restaurant_id,
        "name": current_data.get("name", restaurant.restaurant_id),
        "role": restaurant.role,
        "data": current_data,
        "story": current_data.get("restaurant_story"),
        "menu": current_data.get("menu", []),
        "faq": current_data.get("faq", []),
        "opening_hours": current_data.get("opening_hours", {}),
        "restaurant_data": current_data
    }