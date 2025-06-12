# services/restaurant_service.py

from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
from pinecone_utils import insert_restaurant_data
from schemas.restaurant import RestaurantCreateRequest
from auth import hash_password

KNOWN_ALLERGENS = {"milk", "peanuts", "egg", "wheat", "soy", "fish", "shellfish", "tree nuts", "sesame", "mustard"}

def apply_menu_fallbacks(menu_items: list) -> list:
    """Apply fallbacks to menu items to ensure all required fields exist."""
    def infer_allergens(ingredients):
        """Infer allergens from ingredients list."""
        if not ingredients:
            return []
        return [allergen for allergen in KNOWN_ALLERGENS 
                if any(allergen.lower() in ingredient.lower() for ingredient in ingredients)]

    fallback_items = []
    for item in menu_items:
        try:
            # Handle both dict and object types
            if hasattr(item, 'dict'):
                item_dict = item.dict()
            elif isinstance(item, dict):
                item_dict = item.copy()
            else:
                print(f"Warning: Unexpected item type: {type(item)}")
                continue
            
            # Apply fallbacks for all required fields
            item_dict["name"] = item_dict.get("name") or item_dict.get("dish", "Unknown Dish")
            item_dict["price"] = item_dict.get("price") or "Price not available"
            item_dict["ingredients"] = item_dict.get("ingredients") or ["Not specified"]
            item_dict["description"] = item_dict.get("description") or "No description provided"
            
            # Handle allergens with inference
            if not item_dict.get("allergens"):
                inferred = infer_allergens(item_dict["ingredients"])
                item_dict["allergens"] = inferred if inferred else []
            
            fallback_items.append(item_dict)
            
        except Exception as e:
            print(f"Error processing menu item {item}: {e}")
            # Add a minimal fallback item to prevent complete failure
            fallback_items.append({
                "name": "Menu Item (Error)",
                "price": "Unknown",
                "ingredients": ["Not available"],
                "description": "Unable to process item details",
                "allergens": []
            })
    
    return fallback_items

def validate_menu_data(menu_items: list) -> bool:
    """Validate that all menu items have required fields."""
    required_fields = ['name', 'ingredients', 'description', 'price', 'allergens']
    
    for i, item in enumerate(menu_items):
        if not isinstance(item, dict):
            raise ValueError(f"Menu item {i} is not a dictionary: {item}")
        
        missing_fields = [field for field in required_fields if field not in item]
        if missing_fields:
            raise ValueError(f"Menu item {i} missing required fields: {missing_fields}")
    
    return True

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

    # Prepare data with fallbacks
    data = req.data.dict()
    if "menu" in data and data["menu"]:
        try:
            data["menu"] = apply_menu_fallbacks(data["menu"])
            # Validate the processed menu
            validate_menu_data(data["menu"])
            print(f"Successfully processed {len(data['menu'])} menu items")
        except Exception as e:
            print(f"Error processing menu data: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid menu data: {str(e)}"
            )
    
    # Create restaurant record
    restaurant = models.Restaurant(
        restaurant_id=req.restaurant_id,
        data=data,
        password=hashed_pw,
        role=req.role or "owner"  # Default to "owner" if not specified
    )
    
    try:
        db.add(restaurant)
        db.commit()
        db.refresh(restaurant)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Database error: {str(e)}"
        )

    # Inject into Pinecone (only for owners, not staff)
    if restaurant.role == "owner":
        try:
            insert_restaurant_data(req.restaurant_id, data)
        except Exception as e:
            print(f"Warning: Pinecone insertion failed: {e}")
            # Don't fail the entire operation for Pinecone issues

    return {
        "message": "Restaurant registered successfully",
        "restaurant_id": restaurant.restaurant_id,
        "role": restaurant.role
    }

