# services/restaurant_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
from pinecone_utils import insert_restaurant_data
from schemas.restaurant import RestaurantCreateRequest
from auth import hash_password

KNOWN_ALLERGENS = {"milk", "peanuts", "egg", "wheat", "soy", "fish", "shellfish", "tree nuts"}

def apply_menu_fallbacks(menu_items: list) -> list:
    def infer_allergens(ingredients):
        return [i for i in (ingredients or []) if i.lower() in KNOWN_ALLERGENS]

    for item in menu_items:
        item["price"] = item.get("price") or "Unknown"
        item["ingredients"] = item.get("ingredients") or ["Not specified"]
        item["description"] = item.get("description") or "No description provided"
        item["allergens"] = item.get("allergens") or infer_allergens(item["ingredients"])
    return menu_items


def create_restaurant_service(req: RestaurantCreateRequest, db: Session):
    """
    Consolidated restaurant creation service that handles:
    - Duplicate checks
    - Password hashing
    - Database insert
    - Pinecone update
    """
    # Check if restaurant already exists
    existing_restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if existing_restaurant:
        raise HTTPException(
            status_code=400, 
            detail="Restaurant with this ID already exists"
        )
    
    # Hash the incoming password
    hashed_pw = hash_password(req.password)

    # Insert into DB
    # Prepare data with fallbacks
    data = req.data.dict()
    if "menu" in data:
        data["menu"] = apply_menu_fallbacks(data["menu"])

    restaurant = models.Restaurant(
        restaurant_id=req.restaurant_id,
        data=data,

        password=hashed_pw,
        role=req.role or "owner"  # Default to "owner" if not specified
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)

    # Inject into Pinecone (only for owners, not staff)
    if restaurant.role == "owner":
        insert_restaurant_data(req.restaurant_id, data)

    return {
        "message": "Restaurant registered successfully",
        "restaurant_id": restaurant.restaurant_id,
        "role": restaurant.role
    }

