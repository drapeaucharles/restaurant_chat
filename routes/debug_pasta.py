"""
Debug endpoint for pasta search
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import models
from services.mia_chat_service import format_menu_for_context

router = APIRouter(tags=["debug"])

@router.get("/debug/pasta-context/{restaurant_id}")
def debug_pasta_context(restaurant_id: str, db: Session = Depends(get_db)):
    """Debug pasta context building"""
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        return {"error": "Restaurant not found"}
    
    data = restaurant.data or {}
    menu_items = data.get("menu", [])
    
    # Get context for pasta query
    pasta_context = format_menu_for_context(menu_items, "what pasta do you have")
    
    # Also manually search for pasta
    pasta_dishes = []
    for item in menu_items:
        name = item.get('name', '').lower()
        desc = item.get('description', '').lower()
        if any(p in name or p in desc for p in ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']):
            pasta_dishes.append({
                'name': item.get('name'),
                'price': item.get('price'),
                'category': item.get('subcategory')
            })
    
    return {
        "total_menu_items": len(menu_items),
        "pasta_dishes_found": len(pasta_dishes),
        "pasta_dishes": pasta_dishes,
        "context_generated": pasta_context,
        "menu_sample": [item.get('name') for item in menu_items[:30]]
    }