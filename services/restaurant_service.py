# services/restaurant_service.py

from sqlalchemy.orm import Session
from sqlalchemy import text
from fastapi import HTTPException
import models
from services.embedding_service import embedding_service
from schemas.restaurant import RestaurantCreateRequest
from auth import hash_password
import logging

logger = logging.getLogger(__name__)

KNOWN_ALLERGENS = {"milk", "peanuts", "egg", "wheat", "soy", "fish", "shellfish", "tree nuts", "sesame", "mustard"}

def apply_menu_fallbacks(menu_items: list) -> list:
    """Apply fallbacks to menu items to ensure all required fields exist with new structure."""
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
            
            # Apply new structure with backward compatibility
            processed_item = {}
            
            # Required fields with fallbacks
            processed_item["title"] = (
                item_dict.get("title") or 
                item_dict.get("dish") or 
                item_dict.get("name") or 
                "Unknown Dish"
            )
            
            processed_item["description"] = (
                item_dict.get("description") or 
                "No description provided"
            )
            
            processed_item["price"] = str(
                item_dict.get("price") or "N/A"
            )
            
            # Optional fields with safe defaults
            processed_item["info"] = item_dict.get("info")
            processed_item["category"] = item_dict.get("category")
            processed_item["subcategory"] = item_dict.get("subcategory")
            processed_item["area"] = item_dict.get("area")
            
            # Handle ingredients - ensure it's a list
            ingredients = item_dict.get("ingredients", [])
            if isinstance(ingredients, str):
                processed_item["ingredients"] = [ingredients] if ingredients else []
            else:
                processed_item["ingredients"] = ingredients or []
            
            # Handle allergens with inference
            allergens = item_dict.get("allergens", [])
            if isinstance(allergens, str):
                allergens = [allergens] if allergens else []
            
            if not allergens:
                inferred = infer_allergens(processed_item["ingredients"])
                processed_item["allergens"] = inferred if inferred else []
            else:
                processed_item["allergens"] = allergens
            
            # Keep legacy fields for backward compatibility
            if item_dict.get("dish"):
                processed_item["dish"] = item_dict["dish"]
            if item_dict.get("name"):
                processed_item["name"] = item_dict["name"]
            
            # Preserve photo_url if present
            if item_dict.get("photo_url"):
                processed_item["photo_url"] = item_dict["photo_url"]
            
            fallback_items.append(processed_item)
            
        except Exception as e:
            print(f"Error processing menu item {item}: {e}")
            # Add a minimal fallback item to prevent complete failure
            fallback_items.append({
                "title": "Menu Item (Error)",
                "description": "Unable to process item details",
                "price": "N/A",
                "info": None,
                "category": None,
                "subcategory": None,
                "area": None,
                "ingredients": [],
                "allergens": []
            })
    
    return fallback_items

def validate_menu_data(menu_items: list) -> bool:
    """Validate that all menu items have required fields for new structure."""
    required_fields = ['title', 'description', 'price']
    
    for i, item in enumerate(menu_items):
        if not isinstance(item, dict):
            raise ValueError(f"Menu item {i} is not a dictionary: {item}")
        
        missing_fields = [field for field in required_fields if not item.get(field)]
        if missing_fields:
            raise ValueError(f"Menu item {i} missing required fields: {missing_fields}")
        
        # Validate category if provided
        if item.get('category'):
            valid_categories = ["Breakfast", "Brunch", "Lunch", "Dinner", "Cocktail/Drink List"]
            if item['category'] not in valid_categories:
                raise ValueError(f"Menu item {i} has invalid category: {item['category']}")
        
        # Validate subcategory if provided
        if item.get('subcategory'):
            valid_subcategories = ["starter", "main", "dessert"]
            if item['subcategory'] not in valid_subcategories:
                raise ValueError(f"Menu item {i} has invalid subcategory: {item['subcategory']}")
    
    return True

def create_restaurant_service(req: RestaurantCreateRequest, db: Session):
    """
    Consolidated restaurant creation service that handles:
    - Duplicate checks
    - Password hashing
    - Database insert
    - Pinecone update
    - New menu structure with backward compatibility
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
            print(f"Successfully processed {len(data['menu'])} menu items with new structure")
        except Exception as e:
            print(f"Error processing menu data: {e}")
            raise HTTPException(
                status_code=400,
                detail=f"Invalid menu data: {str(e)}"
            )
    
    # Create restaurant record
    restaurant_data = {
        "restaurant_id": req.restaurant_id,
        "data": data,
        "password": hashed_pw,
        "role": req.role or "owner",  # Default to "owner" if not specified
    }
    
    # Only add business_type if the column exists
    if hasattr(models.Restaurant, 'business_type'):
        restaurant_data["business_type"] = data.get("business_type", "restaurant")
    
    restaurant = models.Restaurant(**restaurant_data)
    
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

    # Create embeddings for menu items (only for owners, not staff)
    if restaurant.role == "owner" and data.get("menu"):
        try:
            # Index menu items for semantic search using HuggingFace
            indexed_count = embedding_service.index_restaurant_menu(
                db=db,
                restaurant_id=req.restaurant_id,
                menu_items=data["menu"]
            )
            db.commit()
            logger.info(f"✅ Created {indexed_count} embeddings for restaurant {req.restaurant_id}")
        except Exception as e:
            logger.error(f"Warning: Embedding creation failed: {e}")
            # Don't fail the entire operation for embedding issues
            db.rollback()

    return {
        "message": "Restaurant registered successfully",
        "restaurant_id": restaurant.restaurant_id,
        "role": restaurant.role
    }

