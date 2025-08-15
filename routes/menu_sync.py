"""
Menu synchronization endpoints for RAG embeddings
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_owner
import models
from services.menu_sync_service import menu_sync_service

router = APIRouter(prefix="/menu-sync", tags=["menu-sync"])

@router.post("/sync/{restaurant_id}")
def sync_restaurant_menu(
    restaurant_id: str,
    db: Session = Depends(get_db)
):
    """
    Manually sync a restaurant's menu to embeddings
    Useful for fixing out-of-sync issues
    """
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Get menu items
    menu_items = restaurant.data.get("menu", []) if restaurant.data else []
    
    if not menu_items:
        return {
            "message": "No menu items to sync",
            "restaurant_id": restaurant_id,
            "indexed": 0
        }
    
    # Sync menu
    result = menu_sync_service.sync_restaurant_menu(db, restaurant_id, menu_items)
    
    if result['success']:
        return {
            "message": "Menu synced successfully",
            "restaurant_id": restaurant_id,
            "indexed": result['indexed']
        }
    else:
        raise HTTPException(
            status_code=500, 
            detail=f"Sync failed: {result.get('error', 'Unknown error')}"
        )

@router.get("/status/{restaurant_id}")
def check_sync_status(
    restaurant_id: str,
    db: Session = Depends(get_db)
):
    """
    Check if a restaurant's menu is properly synced
    """
    status = menu_sync_service.check_sync_status(db, restaurant_id)
    
    if not status['exists']:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return status

@router.post("/sync-all")
def sync_all_restaurants(
    db: Session = Depends(get_db),
    current_owner: models.Restaurant = Depends(get_current_owner)
):
    """
    Sync all restaurants' menus to embeddings
    Admin only endpoint
    """
    # Check if user is admin (you might want to implement proper admin check)
    if current_owner.restaurant_id != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    result = menu_sync_service.sync_all_restaurants(db)
    
    if result['success']:
        return {
            "message": "All restaurants synced successfully",
            "restaurants_synced": result['restaurants_synced'],
            "total_items_indexed": result['total_items_indexed']
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Bulk sync failed: {result.get('error', 'Unknown error')}"
        )

@router.post("/sync-my-restaurant")
def sync_my_restaurant(
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Sync current restaurant's menu to embeddings
    """
    menu_items = current_owner.data.get("menu", []) if current_owner.data else []
    
    if not menu_items:
        return {
            "message": "No menu items to sync",
            "restaurant_id": current_owner.restaurant_id,
            "indexed": 0
        }
    
    result = menu_sync_service.sync_restaurant_menu(
        db, 
        current_owner.restaurant_id, 
        menu_items
    )
    
    if result['success']:
        return {
            "message": "Your menu has been synced successfully",
            "restaurant_id": current_owner.restaurant_id,
            "indexed": result['indexed']
        }
    else:
        raise HTTPException(
            status_code=500,
            detail=f"Sync failed: {result.get('error', 'Unknown error')}"
        )