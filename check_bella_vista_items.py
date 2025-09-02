#!/usr/bin/env python3
"""
Check Bella Vista Restaurant menu items
"""

import os
import sys
from pathlib import Path
import json

# Add parent directory to Python path  
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database import get_db
import models

def check_bella_vista():
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
            
            # Check first few items
            print("First 3 menu items:")
            for i, item in enumerate(menu_items[:3]):
                print(f"\n{i+1}. {item.get('dish') or item.get('title')}:")
                print(f"   is_vegan: {item.get('is_vegan')}")
                print(f"   is_vegetarian: {item.get('is_vegetarian')}")
                print(f"   is_gluten_free: {item.get('is_gluten_free')}")
                
            # Count items with dietary fields
            count_with_fields = sum(1 for item in menu_items if 'is_vegan' in item)
            print(f"\nItems with dietary fields: {count_with_fields}/{len(menu_items)}")
            
            # Show all unique dish names
            print("\nAll dish names:")
            for item in menu_items:
                name = item.get('dish') or item.get('title', 'Unknown')
                has_dietary = '✓' if 'is_vegan' in item else '✗'
                print(f"  {has_dietary} {name}")
                
    finally:
        db.close()

if __name__ == "__main__":
    check_bella_vista()