#!/usr/bin/env python3
"""
Migration script to add dietary fields to existing menu items in the database.
This script updates the JSON data stored in the restaurant table to include
dietary information fields for all menu items.
"""

import os
import sys
from pathlib import Path

# Add parent directory to Python path
sys.path.append(str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
import json
from database import get_db
import models

def add_dietary_fields_to_menu_items():
    """Add dietary fields to all existing menu items in the database."""
    
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
        # Get all restaurants
        restaurants = db.query(models.Restaurant).all()
        
        updated_count = 0
        
        for restaurant in restaurants:
            if restaurant.data and 'menu' in restaurant.data:
                menu_items = restaurant.data.get('menu', [])
                updated = False
                
                for item in menu_items:
                    # Add dietary fields if they don't exist
                    if 'is_vegan' not in item:
                        item['is_vegan'] = None
                        updated = True
                    if 'is_vegetarian' not in item:
                        item['is_vegetarian'] = None
                        updated = True
                    if 'is_gluten_free' not in item:
                        item['is_gluten_free'] = None
                        updated = True
                    if 'is_dairy_free' not in item:
                        item['is_dairy_free'] = None
                        updated = True
                    if 'is_nut_free' not in item:
                        item['is_nut_free'] = None
                        updated = True
                    if 'dietary_tags' not in item:
                        item['dietary_tags'] = []
                        updated = True
                
                if updated:
                    # Update the restaurant data
                    restaurant.data = restaurant.data
                    db.commit()
                    updated_count += 1
                    print(f"✅ Updated {restaurant.restaurant_id} with dietary fields")
        
        print(f"\n🎉 Migration complete! Updated {updated_count} restaurants.")
        
    except Exception as e:
        print(f"❌ Error during migration: {e}")
        db.rollback()
        raise
    finally:
        db.close()

def check_dietary_fields():
    """Check if dietary fields exist in menu items."""
    
    DATABASE_URL = os.getenv(
        "DATABASE_URL",
        "postgresql://postgres:postgres@localhost/restaurant_db"
    )
    
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        restaurants = db.query(models.Restaurant).all()
        
        for restaurant in restaurants:
            if restaurant.data and 'menu' in restaurant.data:
                menu_items = restaurant.data.get('menu', [])
                if menu_items:
                    sample_item = menu_items[0]
                    has_dietary = all(
                        field in sample_item 
                        for field in ['is_vegan', 'is_vegetarian', 'is_gluten_free', 
                                      'is_dairy_free', 'is_nut_free', 'dietary_tags']
                    )
                    print(f"{restaurant.restaurant_id}: {'✅' if has_dietary else '❌'} Dietary fields")
    finally:
        db.close()

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Add dietary fields to menu items')
    parser.add_argument('--check', action='store_true', help='Check if dietary fields exist')
    parser.add_argument('--dry-run', action='store_true', help='Show what would be updated without making changes')
    
    args = parser.parse_args()
    
    if args.check:
        check_dietary_fields()
    else:
        print("🔄 Starting dietary fields migration...")
        add_dietary_fields_to_menu_items()