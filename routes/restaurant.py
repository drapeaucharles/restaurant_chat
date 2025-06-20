"""
Restaurant-related routes and endpoints.
"""

from datetime import timedelta
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_restaurant, get_current_owner, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
import models
from schemas.restaurant import RestaurantCreateRequest, RestaurantData, RestaurantUpdateRequest


router = APIRouter(prefix="/restaurant", tags=["restaurant"])


@router.get("/info")
def get_restaurant_info(restaurant_id: str, db: Session = Depends(get_db)):
    """Get public restaurant information."""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return {
        "restaurant_id": restaurant.restaurant_id,
        "name": restaurant.data.get("name"),
        "story": restaurant.data.get("story"),
        "menu": restaurant.data.get("menu", []),
        "faq": restaurant.data.get("faq", []),
        "opening_hours": restaurant.data.get("opening_hours"),
        "whatsapp_number": restaurant.whatsapp_number
    }


@router.get("/list")
def list_restaurants(db: Session = Depends(get_db)):
    """List all restaurants (public endpoint)."""
    restaurants = db.query(models.Restaurant).all()
    return [
        {
            "restaurant_id": r.restaurant_id,
            "name": r.data.get("name"),
            "story": r.data.get("story"),
            "menu": r.data.get("menu", []),
            "faq": r.data.get("faq", []),
            "opening_hours": r.data.get("opening_hours"),
            "whatsapp_number": r.whatsapp_number
        }
        for r in restaurants
    ]


@router.post("/update")
def update_restaurant(
    restaurant_data: RestaurantUpdateRequest,
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    existing_data = current_owner.data or {}

    # Merge old + new (shallow merge)
    updated_data = {**existing_data, **restaurant_data.data.dict(exclude_unset=True)}
    current_owner.data = updated_data
    
    # Update WhatsApp number if provided
    if restaurant_data.data.whatsapp_number is not None:
        current_owner.whatsapp_number = restaurant_data.data.whatsapp_number

    db.commit()
    db.refresh(current_owner)
    
    return {
        "message": "Restaurant updated successfully",
        "restaurant_id": current_owner.restaurant_id
    }



@router.get("/profile")
def get_restaurant_profile(
    current_restaurant: models.Restaurant = Depends(get_current_restaurant)
):
    """Get current restaurant's profile (protected endpoint)."""
    return {
        "restaurant_id": current_restaurant.restaurant_id,
        "name": current_restaurant.data.get("name"),
        "story": current_restaurant.data.get("story"),
        "menu": current_restaurant.data.get("menu", []),
        "faq": current_restaurant.data.get("faq", []),
        "opening_hours": current_restaurant.data.get("opening_hours"),
        "whatsapp_number": current_restaurant.whatsapp_number
    }


@router.put("/profile")
def update_restaurant_profile(
    restaurant_data: RestaurantData,
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update current restaurant's profile (protected endpoint - owner only)."""
    # Update the restaurant data with new values
    current_owner.data = restaurant_data.dict()
    
    # Update WhatsApp number if provided in the data
    if hasattr(restaurant_data, 'whatsapp_number') and restaurant_data.whatsapp_number:
        current_owner.whatsapp_number = restaurant_data.whatsapp_number
    
    db.commit()
    db.refresh(current_owner)
    
    return {
        "message": "Restaurant profile updated successfully",
        "restaurant_id": current_owner.restaurant_id,
        "data": current_owner.data
    }


@router.delete("/delete")
def delete_restaurant(
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Delete current restaurant (protected endpoint - owner only)."""
    restaurant_id = current_owner.restaurant_id
    
    # Delete the restaurant from the database
    db.delete(current_owner)
    db.commit()
    
    return {
        "message": f"Restaurant {restaurant_id} deleted successfully"
    }

