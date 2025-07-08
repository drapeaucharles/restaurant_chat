"""
Special endpoint to update subcategories for bella_vista_restaurant
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models

router = APIRouter(tags=["admin"])

# Define which dishes should be in which subcategory
DISH_SUBCATEGORIES = {
    # Starters
    "starter": [
        "truffle arancini", "caprese skewers", "calamari fritti", "bruschetta trio",
        "stuffed mushrooms", "shrimp cocktail", "spinach artichoke dip", "beef carpaccio",
        "oysters rockefeller", "french onion soup", "lobster bisque", "caesar salad",
        "greek salad", "roasted beet salad", "minestrone soup", "tom yum soup",
        "gelato trio", "crème brûlée"
    ],
    # Main courses
    "main": [
        "mezze platter", "quinoa power bowl", "spaghetti carbonara", "lobster ravioli",
        "mushroom risotto", "penne arrabbiata", "seafood linguine", "gnocchi gorgonzola",
        "lasagna bolognese", "saffron risotto", "filet mignon", "rack of lamb",
        "osso buco", "duck confit", "beef short ribs", "pork tenderloin",
        "veal piccata", "ribeye steak", "grilled salmon", "sea bass",
        "lobster thermidor", "seared scallops", "tuna steak", "mixed seafood grill",
        "eggplant parmigiana", "vegetable curry", "stuffed bell peppers", 
        "mushroom wellington", "buddha bowl"
    ],
    # Desserts
    "dessert": [
        "tiramisu", "chocolate lava cake", "new york cheesecake"
    ]
}

@router.post("/admin/update-bella-vista-subcategories")
def update_bella_vista_subcategories(
    admin_key: str,
    db: Session = Depends(get_db)
):
    """Update subcategories for bella_vista_restaurant"""
    
    # Simple admin key check
    if admin_key != "BellaVistaAdmin2024!":
        raise HTTPException(status_code=403, detail="Invalid admin key")
    
    # Find the restaurant
    restaurant = db.query(models.Restaurant).filter_by(
        restaurant_id="bella_vista_restaurant"
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Get current data
    data = restaurant.data or {}
    menu_items = data.get('menu', [])
    
    # Create mapping
    subcategory_map = {}
    for subcat, dishes in DISH_SUBCATEGORIES.items():
        for dish in dishes:
            subcategory_map[dish] = subcat
    
    # Update subcategories
    updated_count = 0
    updated_items = []
    
    for item in menu_items:
        # Get dish name
        dish_name = (item.get('dish') or item.get('title', '')).lower()
        
        # Look up subcategory
        subcat = subcategory_map.get(dish_name)
        
        if subcat:
            old_subcat = item.get('subcategory')
            item['subcategory'] = subcat
            if old_subcat != subcat:
                updated_count += 1
                updated_items.append(f"{item.get('dish') or item.get('title')}: {old_subcat} → {subcat}")
        else:
            # Default based on category
            category = item.get('category', '').lower()
            if 'dessert' in category:
                item['subcategory'] = 'dessert'
            elif any(word in category for word in ['appetizer', 'soup', 'salad']):
                item['subcategory'] = 'starter'
            else:
                item['subcategory'] = 'main'
    
    # Update restaurant data - Force SQLAlchemy to detect changes
    data['menu'] = menu_items
    
    # Force update by creating a new dict
    new_data = dict(restaurant.data)
    new_data['menu'] = menu_items
    restaurant.data = new_data
    
    # Mark as modified
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(restaurant, 'data')
    
    db.add(restaurant)
    db.commit()
    db.refresh(restaurant)
    
    # Generate summary
    summary = {}
    for item in menu_items:
        cat = item.get('category', 'Unknown')
        subcat = item.get('subcategory', 'none')
        key = f"{cat} - {subcat}"
        summary[key] = summary.get(key, 0) + 1
    
    return {
        "success": True,
        "updated_count": updated_count,
        "total_items": len(menu_items),
        "updated_items": updated_items,
        "summary": summary
    }