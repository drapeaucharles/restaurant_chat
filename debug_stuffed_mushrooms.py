#!/usr/bin/env python3
"""
Debug why "Stuffed Mushrooms" appears for pasta query
"""
import requests

# Get restaurant menu
response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    # Find Stuffed Mushrooms
    print("Looking for Stuffed Mushrooms in menu...")
    for i, item in enumerate(menu):
        name = item.get('dish', '')
        if 'Stuffed Mushrooms' in name:
            print(f"\nFound at index {i}:")
            print(f"  Name: {name}")
            print(f"  Description: {item.get('description', '')}")
            print(f"  Ingredients: {item.get('ingredients', [])}")
            print(f"  Subcategory: {item.get('subcategory', '')}")
            print(f"  Price: {item.get('price', '')}")
            
    # Check first 20 items
    print("\n" + "=" * 60)
    print("First 20 menu items:")
    for i in range(min(20, len(menu))):
        item = menu[i]
        print(f"{i:2}. {item.get('dish', 'NO NAME')} - {item.get('subcategory', 'NO CAT')}")
        
    # Check if pasta items exist
    print("\n" + "=" * 60)
    print("Pasta items in menu:")
    pasta_count = 0
    for i, item in enumerate(menu):
        name = item.get('dish', '').lower()
        desc = item.get('description', '').lower()
        if any(p in name or p in desc for p in ['pasta', 'spaghetti', 'penne', 'ravioli', 'linguine', 'lasagna', 'gnocchi']):
            pasta_count += 1
            print(f"{i:2}. {item.get('dish', '')}")
            
    print(f"\nTotal pasta items: {pasta_count}")