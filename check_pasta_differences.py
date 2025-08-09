#!/usr/bin/env python3
"""
Check what's different about the two pasta dishes that ARE shown
"""
import requests
import json

response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print("Analyzing pasta dishes...")
    print("=" * 80)
    
    # Get all pasta dishes
    pasta_dishes = []
    for item in menu:
        dish_name = item.get('dish', '')
        desc = item.get('description', '')
        
        if any(p in dish_name.lower() for p in ['spaghetti', 'ravioli', 'penne', 'linguine', 'gnocchi', 'lasagna']):
            pasta_dishes.append({
                'name': dish_name,
                'description': desc,
                'has_pasta_in_desc': 'pasta' in desc.lower(),
                'ingredients': item.get('ingredients', [])
            })
    
    # Show what each has
    for pasta in pasta_dishes:
        print(f"\n{pasta['name']}:")
        print(f"  Has 'pasta' in description: {pasta['has_pasta_in_desc']}")
        print(f"  Description: {pasta['description'][:80]}...")
        
    # Check which ones have "pasta" literally
    print("\n" + "=" * 80)
    print("Summary:")
    with_pasta = [p['name'] for p in pasta_dishes if p['has_pasta_in_desc']]
    without_pasta = [p['name'] for p in pasta_dishes if not p['has_pasta_in_desc']]
    
    print(f"\nHas 'pasta' in description: {with_pasta}")
    print(f"Does NOT have 'pasta' in description: {without_pasta}")
    
    # The two that show up
    print(f"\n\nThe AI shows only: Spaghetti Carbonara, Lobster Ravioli")
    print("These are the first two pasta dishes that have 'pasta' in their description!")
    
else:
    print(f"Error: {response.status_code}")