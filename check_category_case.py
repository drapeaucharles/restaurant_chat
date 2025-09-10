#!/usr/bin/env python3
"""
Check category case sensitivity issue
"""
import psycopg2
import json

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()
cur.execute("""
    SELECT data->'menu' AS menu 
    FROM businesses 
    WHERE business_id = 'bella_vista_restaurant'
""")
menu_items = cur.fetchone()[0]
cur.close()
conn.close()

print("Checking seafood items and their categories:")
print("=" * 50)

for item in menu_items:
    categories = item.get('restaurant_categories', [])
    if 'Seafood' in categories:
        dish_name = item.get('dish')
        print(f"\n{dish_name}:")
        print(f"  Categories: {categories}")
        print(f"  Categories lowercase: {[c.lower() for c in categories]}")
        
        # Check if "seafood" (lowercase) is in lowercase categories
        categories_lower = [c.lower() for c in categories]
        food_type = "seafood"
        
        print(f"  'seafood' in categories_lower: {food_type in categories_lower}")
        
print("\n\nTesting the exact condition from code:")
print("food_type = 'seafood'")
print("For Grilled Salmon with categories ['Fish', 'Seafood', 'Healthy']:")
categories = ['Fish', 'Seafood', 'Healthy']
categories_lower = [cat.lower() for cat in categories]
print(f"  categories_lower = {categories_lower}")
print(f"  'seafood' in categories_lower = {'seafood' in categories_lower}")