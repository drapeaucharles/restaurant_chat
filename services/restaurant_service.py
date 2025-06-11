# services/restaurant_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
from pinecone_utils import insert_restaurant_data
from schemas.restaurant import RestaurantCreateRequest
from auth import hash_password

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
    restaurant = models.Restaurant(
        restaurant_id=req.restaurant_id,
        data=req.data.dict(),
        password=hashed_pw,
        role=req.role or "owner"  # Default to "owner" if not specified
    )
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)

    # Inject into Pinecone (only for owners, not staff)
    if restaurant.role == "owner":
        insert_restaurant_data(req.restaurant_id, req.data.dict())

    return {
        "message": "Restaurant registered successfully",
        "restaurant_id": restaurant.restaurant_id,
        "role": restaurant.role
    }

