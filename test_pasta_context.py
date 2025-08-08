#!/usr/bin/env python3
"""
Debug why not all pasta dishes are being found
"""
import requests
import json

# Get restaurant data
restaurant_id = "bella_vista_restaurant"
response = requests.get(f"https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id={restaurant_id}")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print(f"Total menu items: {len(menu)}")
    print("\nSearching for pasta dishes:")
    print("-" * 50)
    
    pasta_dishes = []
    for i, item in enumerate(menu):
        name = item.get('name') or item.get('dish', '')
        description = item.get('description', '')
        ingredients = item.get('ingredients', [])
        
        # Check if it's a pasta dish
        name_lower = name.lower()
        desc_lower = description.lower()
        ing_lower = ' '.join(ingredients).lower()
        
        if ('pasta' in name_lower or 'pasta' in desc_lower or 'pasta' in ing_lower or
            'spaghetti' in name_lower or 'linguine' in name_lower or 
            'penne' in name_lower or 'ravioli' in name_lower or
            'lasagna' in name_lower or 'gnocchi' in name_lower):
            
            pasta_dishes.append({
                'index': i,
                'name': name,
                'category': item.get('subcategory', ''),
                'description': description[:60] + '...'
            })
            
    print(f"\nFound {len(pasta_dishes)} pasta dishes:")
    for dish in pasta_dishes:
        print(f"\n{dish['index']}. {dish['name']} ({dish['category']})")
        print(f"   {dish['description']}")
        
    # Test what context would be built
    print("\n" + "=" * 50)
    print("Testing context building for 'what pasta do you have':")
    
    # Simulate the first 20 items check
    found_in_first_20 = []
    for item in menu[:20]:
        name = item.get('name', '').lower()
        if 'pasta' in name or any(p in name for p in ['spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna']):
            found_in_first_20.append(item.get('name'))
    
    print(f"\nIn first 20 items: {found_in_first_20}")
    print(f"Total pasta dishes in menu: {[d['name'] for d in pasta_dishes]}")
    
else:
    print(f"Error: {response.status_code}")