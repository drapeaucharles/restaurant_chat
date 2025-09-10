#!/usr/bin/env python3
"""
Debug is_safe_for_customer logic
"""
import psycopg2
import json

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

# Simulate customer with shellfish allergy
customer_allergies = ['shellfish']

def is_safe_for_customer(item, customer_allergies):
    """Replicate the safety check logic"""
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

# Test with menu items
conn = psycopg2.connect(DATABASE_URL)
cur = conn.cursor()

cur.execute("""
    SELECT data->'menu' AS menu 
    FROM businesses 
    WHERE business_id = 'bella_vista_restaurant'
""")

menu_items = cur.fetchone()[0]

print("Testing is_safe_for_customer with shellfish allergy...")
print("\nItems marked as UNSAFE (should only be actual shellfish):")

unsafe_count = 0
safe_fish = []

for item in menu_items:
    dish_name = item.get('dish', '')
    allergens = item.get('allergens', [])
    ingredients = item.get('ingredients', [])
    categories = item.get('restaurant_categories', [])
    
    is_safe = is_safe_for_customer(item, customer_allergies)
    
    if not is_safe:
        unsafe_count += 1
        print(f"\n{unsafe_count}. {dish_name}")
        print(f"   Allergens: {allergens}")
        print(f"   Ingredients (first 3): {ingredients[:3]}")
        
        # Check why it's unsafe
        allergen_match = any('shellfish' in a.lower() for a in allergens)
        ingredient_match = 'shellfish' in ' '.join(ingredients).lower()
        
        print(f"   Unsafe because: allergen={allergen_match}, ingredient={ingredient_match}")
    
    # Track safe fish items
    elif 'Fish' in categories or 'Seafood' in categories:
        safe_fish.append(dish_name)

print(f"\n\nTotal items marked as unsafe: {unsafe_count}")
print(f"\nFish/Seafood items that ARE safe: {len(safe_fish)}")
for fish in safe_fish[:5]:
    print(f"- {fish}")

cur.close()
conn.close()