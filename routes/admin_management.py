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
    
    logger.info(f"Admin {current_admin.restaurant_id} fetching all restaurants")
    
    restaurants = db.query(models.Restaurant).all()
    logger.info(f"Found {len(restaurants)} restaurants")
    
    # Format the response
    result = []
    for restaurant in restaurants:
        data = restaurant.data or {}
        result.append({
            "restaurant_id": restaurant.restaurant_id,
            "name": data.get("name", restaurant.restaurant_id),
            "role": restaurant.role,
            "business_type": restaurant.business_type or data.get("business_type", "restaurant")
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
        logger.info(f"Restaurant data has {len(restaurant.data)} keys: {list(restaurant.data.keys())}")
        if 'name' in restaurant.data:
            logger.info(f"Restaurant name from DB: {restaurant.data.get('name')}")
        if 'menu' in restaurant.data and restaurant.data['menu']:
            first_item = restaurant.data['menu'][0]
            logger.info(f"First menu item: {first_item.get('dish', 'NO DISH')} / {first_item.get('title', 'NO TITLE')}")
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
    
    # Update restaurant data - ensure we preserve all fields
    current_data = restaurant.data or {}
    logger.info(f"Current data has {len(current_data)} keys: {list(current_data.keys())[:5]}...")
    
    # Create a new dict to ensure proper assignment
    updated_data = dict(current_data)
    updated_data.update(new_data)
    
    # Explicitly set the data to ensure SQLAlchemy detects the change
    restaurant.data = None  # Force SQLAlchemy to detect change
    db.flush()  # Flush the None
    restaurant.data = updated_data  # Set the new data
    
    logger.info(f"After update, data has {len(updated_data)} keys: {list(updated_data.keys())}")
    
    # Also update separate fields if they exist in the update
    if 'whatsapp_number' in new_data:
        restaurant.whatsapp_number = new_data['whatsapp_number']
    if 'rag_mode' in new_data:
        restaurant.rag_mode = new_data['rag_mode']
    if 'business_type' in new_data:
        restaurant.business_type = new_data['business_type']
    
    # Verify the update
    logger.info(f"Updated data has {len(restaurant.data)} keys")
    if 'menu' in restaurant.data:
        logger.info(f"Menu has {len(restaurant.data['menu'])} items")
    if 'name' in restaurant.data:
        logger.info(f"Restaurant name is now: {restaurant.data['name']}")
    
    # Force commit and verify
    try:
        db.commit()
        logger.info(f"Database commit successful")
    except Exception as e:
        logger.error(f"Database commit failed: {str(e)}")
        db.rollback()
        raise HTTPException(status_code=500, detail="Failed to save changes")
    
    db.refresh(restaurant)
    
    # Verify the update actually saved
    verify_restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if verify_restaurant and verify_restaurant.data:
        logger.info(f"Verification - Restaurant has {len(verify_restaurant.data)} keys after commit")
        if 'menu' in verify_restaurant.data and verify_restaurant.data['menu']:
            first_item = verify_restaurant.data['menu'][0]
            logger.info(f"Verification - First menu item after commit: {first_item.get('dish', 'NO DISH')}")
    
    logger.info(f"Restaurant {restaurant_id} updated successfully by admin")
    
    # Sync menu to embeddings if updated
    if "menu" in new_data and new_data["menu"]:
        try:
            # Import here to avoid circular dependency
            from sqlalchemy import text
            
            # Clear existing embeddings
            db.execute(text("""
                DELETE FROM menu_embeddings 
                WHERE restaurant_id = :restaurant_id
            """), {"restaurant_id": restaurant_id})
            
            # Generate new embeddings - check if service is available
            try:
                from services.embedding_service_universal import UniversalEmbeddingService
                embedding_service = UniversalEmbeddingService()
                if hasattr(embedding_service, 'index_restaurant_menu'):
                    indexed = embedding_service.index_restaurant_menu(
                        db=db,
                        restaurant_id=restaurant_id,
                        menu_items=new_data["menu"]
                    )
                    logger.info(f"Indexed {indexed} menu items for restaurant {restaurant_id}")
                else:
                    logger.warning("Embedding service does not support menu indexing")
            except ImportError:
                logger.warning("Embedding service not available")
        except Exception as e:
            logger.error(f"Failed to update embeddings for {restaurant_id}: {str(e)}")
            # Don't fail the update if embeddings fail
    
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