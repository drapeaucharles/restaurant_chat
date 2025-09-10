#!/usr/bin/env python3
"""
Fix Calamari allergen - should be shellfish not just seafood
"""
import psycopg2
import json
from psycopg2.extras import Json

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

# Get current menu data
cur.execute("""
    SELECT data 
    FROM businesses 
    WHERE business_id = 'bella_vista_restaurant'
""")

result = cur.fetchone()
data = result[0]
menu_items = data.get('menu', [])

print("Fixing Calamari allergen...")

for item in menu_items:
    if 'calamari' in item.get('dish', '').lower():
        print(f"\nFound: {item.get('dish')}")
        print(f"Current allergens: {item.get('allergens', [])}")
        
        # Update allergens to include shellfish
        item['allergens'] = ['shellfish', 'gluten']
        
        print(f"New allergens: {item.get('allergens', [])}")

# Update the database
data['menu'] = menu_items
cur.execute("""
    UPDATE businesses 
    SET data = %s 
    WHERE business_id = 'bella_vista_restaurant'
""", (Json(data),))

conn.commit()
print("\n✅ Successfully updated Calamari allergen to include shellfish!")

cur.close()
conn.close()