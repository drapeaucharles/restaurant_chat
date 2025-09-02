#!/usr/bin/env python3
"""
Update Bella Vista Restaurant menu items with dietary information
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import json
from database import get_db
import models

# Bella Vista dietary information based on ingredients
BELLA_VISTA_DIETARY_INFO = {
    # Appetizers
    "Truffle Arancinidsa": {  # Fixed typo
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains breadcrumbs
        "is_dairy_free": False,   # Contains cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Truffle Arancini": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains breadcrumbs
        "is_dairy_free": False,   # Contains cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Caprese Skewers": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains mozzarella
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Calamari Fritti": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": False,  # Breaded
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Bruschetta Trio": {
        "is_vegan": False,        # Traditional has cheese
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains bread
        "is_dairy_free": False,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Stuffed Mushrooms": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains breadcrumbs
        "is_dairy_free": False,   # Contains parmesan
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Shrimp Cocktail": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo"]
    },
    "Spinach Artichoke Dip": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,   # Dip itself is GF
        "is_dairy_free": False,   # Contains cream cheese
        "is_nut_free": True,
        "dietary_tags": ["keto-friendly"]
    },
    "Beef Carpaccio": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains parmesan
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Mezze Platter": {
        "is_vegan": False,        # Contains tzatziki (yogurt)
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains pita
        "is_dairy_free": False,
        "is_nut_free": False,     # May contain tahini
        "dietary_tags": []
    },
    "Oysters Rockefeller": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains butter
        "is_nut_free": True,
        "dietary_tags": ["keto"]
    },
    
    # Soups
    "Minestrone Soup": {
        "is_vegan": True,         # Traditional minestrone is vegan
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "French Onion Soup": {
        "is_vegan": False,
        "is_vegetarian": False,  # Contains beef broth
        "is_gluten_free": False,  # Contains bread
        "is_dairy_free": False,   # Contains gruyere
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Lobster Bisque": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains cream
        "is_nut_free": True,
        "dietary_tags": []
    },
    
    # Salads
    "Caesar Salad": {
        "is_vegan": False,
        "is_vegetarian": False,   # Contains anchovies
        "is_gluten_free": False,  # Contains croutons
        "is_dairy_free": False,   # Contains parmesan
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Greek Salad": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains feta
        "is_nut_free": True,
        "dietary_tags": ["keto"]
    },
    "Beet & Goat Cheese Salad": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains goat cheese
        "is_nut_free": False,     # Contains walnuts
        "dietary_tags": []
    },
    "Roasted Beet Salad": {  # Same as above
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains goat cheese
        "is_nut_free": False,     # Contains walnuts
        "dietary_tags": []
    },
    "Quinoa Power Bowl": {
        "is_vegan": True,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,      # Assuming no nuts
        "dietary_tags": ["paleo"]
    },
    "Tom Yum Soup": {
        "is_vegan": False,
        "is_vegetarian": False,   # Contains shrimp
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    
    # Pasta
    "Spaghetti Carbonara": {
        "is_vegan": False,
        "is_vegetarian": False,   # Contains pancetta
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": False,   # Contains cheese and eggs
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Linguine alle Vongole": {
        "is_vegan": False,
        "is_vegetarian": False,   # Contains clams
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Penne Arrabbiata": {
        "is_vegan": True,         # Traditional is vegan
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Fettuccine Alfredo": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": False,   # Heavy cream and parmesan
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Gnocchi Sorrentina": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Gnocchi contains flour
        "is_dairy_free": False,   # Contains mozzarella
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Lobster Ravioli": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": False,   # Contains cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Seafood Linguine": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Gnocchi Gorgonzola": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains flour
        "is_dairy_free": False,   # Contains gorgonzola
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Lasagna Bolognese": {
        "is_vegan": False,
        "is_vegetarian": False,  # Contains meat sauce
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": False,   # Contains cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Mushroom Risotto": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains parmesan and butter
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Saffron Risotto": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains parmesan and butter
        "is_nut_free": True,
        "dietary_tags": []
    },
    
    # Risotto
    "Wild Mushroom Risotto": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains parmesan and butter
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Seafood Risotto": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains butter
        "is_nut_free": True,
        "dietary_tags": []
    },
    
    # Meat
    "Osso Buco": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo"]
    },
    "Chicken Marsala": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": False,  # Flour coating
        "is_dairy_free": False,   # Contains butter
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Grilled Ribeye": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Lamb Chops": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Filet Mignon": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Rack of Lamb": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Duck Confit": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo"]
    },
    "Beef Short Ribs": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Pork Tenderloin": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Veal Piccata": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": False,  # Flour coating
        "is_dairy_free": False,   # Contains butter
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Ribeye Steak": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    
    # Seafood
    "Branzino al Sale": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Lobster Thermidor": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains cream sauce
        "is_nut_free": True,
        "dietary_tags": ["keto"]
    },
    "Grilled Octopus": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Tuna Steak": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,      # Assuming no sesame crust
        "dietary_tags": ["paleo", "keto"]
    },
    "Grilled Salmon": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Sea Bass": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    "Seared Scallops": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Usually served with butter
        "is_nut_free": True,
        "dietary_tags": ["keto"]
    },
    "Mixed Seafood Grill": {
        "is_vegan": False,
        "is_vegetarian": False,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": ["paleo", "keto"]
    },
    
    # Vegetarian
    "Eggplant Parmesan": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Breaded
        "is_dairy_free": False,   # Contains cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Vegetable Lasagna": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains pasta
        "is_dairy_free": False,   # Contains ricotta and mozzarella
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Stuffed Bell Peppers": {
        "is_vegan": True,         # Assuming vegan stuffing
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Eggplant Parmigiana": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Breaded
        "is_dairy_free": False,   # Contains cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Vegetable Curry": {
        "is_vegan": True,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": True,      # Assuming no nuts
        "dietary_tags": []
    },
    "Mushroom Wellington": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Puff pastry
        "is_dairy_free": False,   # Contains butter in pastry
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Buddha Bowl": {
        "is_vegan": True,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": True,
        "is_nut_free": False,     # Usually contains nuts/seeds
        "dietary_tags": ["paleo"]
    },
    
    # Desserts
    "Tiramisu": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains ladyfingers
        "is_dairy_free": False,   # Contains mascarpone
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Panna Cotta": {
        "is_vegan": False,
        "is_vegetarian": False,   # Contains gelatin
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains cream
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Chocolate Lava Cake": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Contains flour
        "is_dairy_free": False,   # Contains butter and cream
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Crème Brûlée": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains cream
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Gelato Selection": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains milk
        "is_nut_free": False,     # May contain nuts depending on flavor
        "dietary_tags": []
    },
    "New York Cheesecake": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": False,  # Graham cracker crust
        "is_dairy_free": False,   # Contains cream cheese
        "is_nut_free": True,
        "dietary_tags": []
    },
    "Gelato Trio": {
        "is_vegan": False,
        "is_vegetarian": True,
        "is_gluten_free": True,
        "is_dairy_free": False,   # Contains milk
        "is_nut_free": False,     # May contain nuts
        "dietary_tags": []
    }
}

def update_bella_vista_dietary():
    """Update Bella Vista restaurant menu items with dietary information"""
    
    # Get database URL from environment or use default
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/restaurant_db"
    )
    
    # Create engine and session
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # Get Bella Vista restaurant
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == "bella_vista_restaurant"
        ).first()
        
        if not restaurant:
            print("❌ Bella Vista restaurant not found!")
            return
        
        if not restaurant.data or 'menu' not in restaurant.data:
            print("❌ Bella Vista has no menu data!")
            return
        
        menu_items = restaurant.data.get('menu', [])
        updated_count = 0
        
        print(f"🔄 Updating {len(menu_items)} menu items...")
        
        for item in menu_items:
            dish_name = item.get('dish') or item.get('title', '')
            
            if dish_name in BELLA_VISTA_DIETARY_INFO:
                dietary_info = BELLA_VISTA_DIETARY_INFO[dish_name]
                
                # Update item with dietary information
                item.update(dietary_info)
                updated_count += 1
                
                print(f"✅ Updated '{dish_name}' with dietary info")
            else:
                print(f"⚠️  No dietary info found for '{dish_name}'")
        
        # Save changes - need to create new dict to trigger update
        from sqlalchemy.orm.attributes import flag_modified
        flag_modified(restaurant, "data")
        db.commit()
        
        print(f"\n🎉 Successfully updated {updated_count}/{len(menu_items)} menu items!")
        
    except Exception as e:
        print(f"❌ Error updating Bella Vista: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def verify_dietary_update():
    """Verify the dietary information was updated correctly"""
    
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/restaurant_db"
    )
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == "bella_vista_restaurant"
        ).first()
        
        if restaurant and restaurant.data and 'menu' in restaurant.data:
            menu_items = restaurant.data.get('menu', [])
            
            vegan_count = sum(1 for item in menu_items if item.get('is_vegan') is True)
            vegetarian_count = sum(1 for item in menu_items if item.get('is_vegetarian') is True)
            gluten_free_count = sum(1 for item in menu_items if item.get('is_gluten_free') is True)
            
            print("\n📊 Dietary Summary:")
            print(f"   Vegan items: {vegan_count}")
            print(f"   Vegetarian items: {vegetarian_count}")
            print(f"   Gluten-free items: {gluten_free_count}")
            
            print("\n🌱 Vegan Options:")
            for item in menu_items:
                if item.get('is_vegan') is True:
                    print(f"   - {item.get('dish') or item.get('title')}")
            
    finally:
        db.close()

if __name__ == "__main__":
    print("🍽️  Updating Bella Vista Restaurant dietary information...")
    update_bella_vista_dietary()
    print("\n📋 Verifying update...")
    verify_dietary_update()