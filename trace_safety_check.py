#!/usr/bin/env python3
"""
Trace through why fish are marked unsafe
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

# Simulate is_safe_for_customer with shellfish allergy
customer_allergies = ['shellfish']

def is_safe_for_customer(item):
    """Exact copy of backend function"""
    if not customer_allergies:
        return True
    
    item_allergens = [a.lower() for a in item.get('allergens', [])]
    ingredients_text = ' '.join(item.get('ingredients', [])).lower()
    
    for allergy in customer_allergies:
        allergy_lower = allergy.lower()
        # Check allergens list
        if any(allergy_lower in allergen for allergen in item_allergens):
            return False
        # Check ingredients
        if allergy_lower in ingredients_text:
            return False
    
    return True

# Test specific fish items
fish_items = ['Grilled Salmon', 'Sea Bass', 'Tuna Steak']

print("Testing fish items for shellfish safety:")
print("=" * 50)

for item in menu_items:
    if item.get('dish') in fish_items:
        dish_name = item.get('dish')
        allergens = item.get('allergens', [])
        ingredients = item.get('ingredients', [])
        is_safe = is_safe_for_customer(item)
        
        print(f"\n{dish_name}:")
        print(f"  Allergens: {allergens}")
        print(f"  Allergens lower: {[a.lower() for a in allergens]}")
        print(f"  Ingredients: {ingredients[:3]}...")
        print(f"  Ingredients text: '{' '.join(ingredients).lower()[:50]}...'")
        print(f"  Is safe: {is_safe}")
        
        # Detailed check
        allergens_lower = [a.lower() for a in allergens]
        has_shellfish_allergen = any('shellfish' in a for a in allergens_lower)
        ingredients_text = ' '.join(ingredients).lower()
        has_shellfish_ingredient = 'shellfish' in ingredients_text
        
        print(f"  Has 'shellfish' in allergens: {has_shellfish_allergen}")
        print(f"  Has 'shellfish' in ingredients: {has_shellfish_ingredient}")