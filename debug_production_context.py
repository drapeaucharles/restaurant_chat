#!/usr/bin/env python3
"""
Debug what context is actually being built in production
"""
import requests
import json

# Get restaurant data
print("Fetching restaurant data...")
response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print(f"Total menu items: {len(menu)}")
    
    # Check specific pasta items
    print("\nChecking pasta items in menu:")
    print("-" * 60)
    
    pasta_items = []
    for i, item in enumerate(menu):
        name = item.get('name', '')
        desc = item.get('description', '')
        ingredients = item.get('ingredients', [])
        
        name_lower = name.lower()
        
        # Check if it's a pasta dish
        is_pasta = False
        pasta_keywords = ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']
        
        # Check name
        if any(k in name_lower for k in pasta_keywords):
            is_pasta = True
            reason = "name"
        # Check description
        elif any(k in desc.lower() for k in pasta_keywords):
            is_pasta = True
            reason = "description"
        # Check ingredients
        elif any(k in ' '.join(str(ing).lower() for ing in ingredients) for k in pasta_keywords):
            is_pasta = True
            reason = "ingredients"
            
        if is_pasta:
            print(f"\n{i}. {name}")
            print(f"   Found in: {reason}")
            print(f"   Description: {desc[:80]}...")
            if 'ingredients' in reason:
                print(f"   Ingredients: {ingredients}")
            pasta_items.append(name)
    
    print(f"\n\nTotal pasta items found: {len(pasta_items)}")
    print(f"Items: {pasta_items}")
    
    # Now check what happens with the first 20 items
    print("\n" + "=" * 60)
    print("Checking first 20 items (old logic):")
    pasta_in_first_20 = []
    for item in menu[:20]:
        name = item.get('name', '')
        if any(k in name.lower() for k in ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']):
            pasta_in_first_20.append(name)
    
    print(f"Pasta in first 20: {pasta_in_first_20}")
    
    # Check what has "pasta" literally in the text
    print("\n" + "=" * 60)
    print("Items with 'pasta' literally in name/description/ingredients:")
    literal_pasta = []
    for item in menu:
        name = item.get('name', '')
        desc = item.get('description', '')
        ingredients = str(item.get('ingredients', []))
        
        full_text = f"{name} {desc} {ingredients}".lower()
        if 'pasta' in full_text:
            literal_pasta.append(name)
            print(f"- {name}")
            
    print(f"\nTotal with literal 'pasta': {len(literal_pasta)}")
    
else:
    print(f"Error: {response.status_code}")