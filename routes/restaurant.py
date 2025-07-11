"""
Restaurant-related routes and endpoints.
"""

from datetime import timedelta
from typing import List, Optional
import json

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from sqlalchemy.orm import Session

from auth import get_current_restaurant, get_current_owner, ACCESS_TOKEN_EXPIRE_MINUTES
from database import get_db
import models
from schemas.restaurant import RestaurantUpdateRequest, RestaurantProfileUpdate, MenuItem
from services.restaurant_service import apply_menu_fallbacks
from services.file_service import save_upload_file, delete_upload_file
from pinecone_utils import insert_restaurant_data, index_menu_items


def process_menu_for_response(menu_data):
    """Process menu data for API responses, ensuring new structure compatibility."""
    if not menu_data:
        return []
    
    # Apply fallbacks to ensure consistent structure
    processed_menu = apply_menu_fallbacks(menu_data)
    
    # Process each item
    for i, item in enumerate(processed_menu):
        # Keep all fields, including None values for certain important fields
        filtered_item = {}
        for k, v in item.items():
            # Always include these fields even if None
            if k in ['subcategory', 'category', 'area', 'info']:
                filtered_item[k] = v
            # For other fields, only include if not None
            elif v is not None:
                filtered_item[k] = v
        
        # Convert relative photo URLs to absolute URLs
        if filtered_item.get("photo_url") and not filtered_item["photo_url"].startswith("http"):
            # Assuming the backend is hosted at the same domain
            filtered_item["photo_url"] = f"https://restaurantchat-production.up.railway.app{filtered_item['photo_url']}"
        
        processed_menu[i] = filtered_item
    
    return processed_menu


router = APIRouter(prefix="/restaurant", tags=["restaurant"])


@router.get("/test-auth")
def test_auth(authorization: str = Header(None)):
    """Test endpoint to debug authentication without dependencies."""
    from auth import decode_token
    
    if not authorization:
        return {"error": "No Authorization header"}
    
    if not authorization.startswith("Bearer "):
        return {"error": "Authorization must start with 'Bearer '"}
    
    token = authorization.split(" ")[1]
    
    try:
        payload = decode_token(token)
        if payload:
            return {
                "status": "Token valid",
                "payload": payload,
                "token_preview": token[:20] + "..."
            }
        else:
            return {"error": "Token decode returned None"}
    except Exception as e:
        return {"error": f"Token decode error: {type(e).__name__}: {str(e)}"}


@router.get("/info")
def get_restaurant_info(restaurant_id: str, db: Session = Depends(get_db)):
    """Get public restaurant information with processed menu structure."""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    return {
        "restaurant_id": restaurant.restaurant_id,
        "name": restaurant.data.get("name"),
        "story": restaurant.data.get("story"),
        "menu": process_menu_for_response(restaurant.data.get("menu", [])),
        "faq": restaurant.data.get("faq", []),
        "opening_hours": restaurant.data.get("opening_hours"),
        "whatsapp_number": restaurant.whatsapp_number,
        "restaurant_categories": getattr(restaurant, 'restaurant_categories', None) or []
    }


@router.get("/list")
def list_restaurants(db: Session = Depends(get_db)):
    """List all restaurants (public endpoint) with processed menu structure."""
    restaurants = db.query(models.Restaurant).all()
    return [
        {
            "restaurant_id": r.restaurant_id,
            "name": r.data.get("name"),
            "story": r.data.get("story"),
            "menu": process_menu_for_response(r.data.get("menu", [])),
            "faq": r.data.get("faq", []),
            "opening_hours": r.data.get("opening_hours"),
            "whatsapp_number": r.whatsapp_number,
            "restaurant_categories": getattr(r, 'restaurant_categories', None) or []
        }
        for r in restaurants
    ]


@router.post("/update")
def update_restaurant(
    restaurant_data: RestaurantUpdateRequest,
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Update restaurant data with menu structure processing."""
    existing_data = current_owner.data or {}

    # Get the new data
    new_data = restaurant_data.data.model_dump(exclude_unset=True)
    
    # Process menu if provided
    if "menu" in new_data and new_data["menu"]:
        new_data["menu"] = apply_menu_fallbacks(new_data["menu"])

    # Merge old + new (shallow merge)
    updated_data = {**existing_data, **new_data}
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
    """Get current restaurant's profile (protected endpoint) with processed menu."""
    print(f"Profile accessed by restaurant: {current_restaurant.restaurant_id}")
    return {
        "restaurant_id": current_restaurant.restaurant_id,
        "name": current_restaurant.data.get("name"),
        "story": current_restaurant.data.get("story"),
        "menu": process_menu_for_response(current_restaurant.data.get("menu", [])),
        "faq": current_restaurant.data.get("faq", []),
        "opening_hours": current_restaurant.data.get("opening_hours"),
        "whatsapp_number": current_restaurant.whatsapp_number,
        "restaurant_categories": getattr(current_restaurant, 'restaurant_categories', None) or []
    }


@router.put("/profile")
def update_restaurant_profile_new(
    payload: RestaurantProfileUpdate,
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Update restaurant profile for authenticated owner with menu processing.
    New implementation with structured opening hours and success response.
    """
    # Process menu items with new structure
    processed_menu = apply_menu_fallbacks([item.model_dump() for item in payload.menu])
    
    # Prepare the data dictionary for the restaurant
    updated_data = {
        "name": payload.name,
        "story": payload.story,
        "menu": processed_menu,
        "faq": [faq.model_dump() for faq in payload.faq] if payload.faq else [],
    }
    
    # Handle opening hours - convert to dict if provided
    if payload.opening_hours:
        updated_data["opening_hours"] = payload.opening_hours.model_dump(exclude_none=True)
    
    # Update the restaurant data
    current_owner.data = updated_data
    
    # Update WhatsApp number if provided
    if payload.whatsapp_number:
        current_owner.whatsapp_number = payload.whatsapp_number
    
    # Update restaurant categories if provided (when column exists)
    if hasattr(payload, 'restaurant_categories') and hasattr(current_owner, 'restaurant_categories'):
        current_owner.restaurant_categories = payload.restaurant_categories
    
    # Commit changes to database
    db.commit()
    db.refresh(current_owner)
    
    # Update Pinecone indexes
    try:
        # Update restaurant context
        insert_restaurant_data(current_owner.restaurant_id, updated_data)
        
        # Re-index menu items for semantic search
        if processed_menu:
            indexed_count = index_menu_items(current_owner.restaurant_id, processed_menu)
            print(f"✅ Re-indexed {indexed_count} menu items for restaurant {current_owner.restaurant_id}")
    except Exception as e:
        print(f"Warning: Pinecone update failed: {e}")
        # Don't fail the operation for Pinecone issues
    
    return {"success": True}


@router.put("/profile/multipart")
async def update_restaurant_profile_multipart(
    restaurant_data: str = Form(...),
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db),
    menu_photo_0: Optional[UploadFile] = File(None),
    menu_photo_1: Optional[UploadFile] = File(None),
    menu_photo_2: Optional[UploadFile] = File(None),
    menu_photo_3: Optional[UploadFile] = File(None),
    menu_photo_4: Optional[UploadFile] = File(None),
    menu_photo_5: Optional[UploadFile] = File(None),
    menu_photo_6: Optional[UploadFile] = File(None),
    menu_photo_7: Optional[UploadFile] = File(None),
    menu_photo_8: Optional[UploadFile] = File(None),
    menu_photo_9: Optional[UploadFile] = File(None),
):
    """
    Update restaurant profile with multipart/form-data support for image uploads.
    Accepts up to 10 menu item photos.
    """
    try:
        # Parse the JSON data
        data = json.loads(restaurant_data)
        restaurant_info = data.get("restaurant_data", {})
        
        # Collect all menu photos
        menu_photos = [
            menu_photo_0, menu_photo_1, menu_photo_2, menu_photo_3, menu_photo_4,
            menu_photo_5, menu_photo_6, menu_photo_7, menu_photo_8, menu_photo_9
        ]
        
        # Process menu items and upload photos
        menu_items = restaurant_info.get("menu", [])
        for idx, menu_item in enumerate(menu_items):
            if idx < len(menu_photos) and menu_photos[idx] is not None:
                # Delete old photo if exists
                if "photo_url" in menu_item and menu_item["photo_url"]:
                    delete_upload_file(menu_item["photo_url"])
                
                # Save new photo
                photo_url = await save_upload_file(menu_photos[idx], "menu")
                menu_item["photo_url"] = photo_url
        
        # Apply menu fallbacks
        processed_menu = apply_menu_fallbacks(menu_items)
        
        # Prepare the data dictionary for the restaurant
        updated_data = {
            "name": restaurant_info.get("name"),
            "story": restaurant_info.get("story"),
            "menu": processed_menu,
            "faq": restaurant_info.get("faq", []),
            "opening_hours": restaurant_info.get("opening_hours"),
        }
        
        # Update the restaurant data
        current_owner.data = updated_data
        
        # Update WhatsApp number if provided
        if restaurant_info.get("whatsapp_number"):
            current_owner.whatsapp_number = restaurant_info["whatsapp_number"]
        
        # Commit changes to database
        db.commit()
        db.refresh(current_owner)
        
        return {"success": True}
        
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON data")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


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

