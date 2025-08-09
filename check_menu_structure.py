#!/usr/bin/env python3
"""
Check the actual menu data structure
"""
import requests
import json

response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print("Checking menu item structure...")
    print("First 3 pasta items (indices 18-20):")
    print("-" * 60)
    
    for i in [18, 19, 20, 21]:
        if i < len(menu):
            item = menu[i]
            print(f"\nItem {i}:")
            print(f"  Keys: {list(item.keys())}")
            print(f"  name: '{item.get('name', 'NOT FOUND')}'")
            print(f"  dish: '{item.get('dish', 'NOT FOUND')}'")
            print(f"  description: '{item.get('description', '')[:60]}...'")
            
    # Check which field contains the dish name
    print("\n" + "=" * 60)
    print("Checking field usage across all items:")
    has_name = 0
    has_dish = 0
    has_both = 0
    
    for item in menu:
        if item.get('name'):
            has_name += 1
        if item.get('dish'):
            has_dish += 1
        if item.get('name') and item.get('dish'):
            has_both += 1
            
    print(f"Items with 'name' field: {has_name}")
    print(f"Items with 'dish' field: {has_dish}")
    print(f"Items with both: {has_both}")
    
else:
    print(f"Error: {response.status_code}")