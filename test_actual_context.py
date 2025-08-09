#!/usr/bin/env python3
"""
Test what context is actually being built for different queries
"""
import sys
sys.path.append('/home/charles-drapeau/Documents/Project/Restaurant/BackEnd')

import requests
import json

# Get restaurant data
response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print(f"Total menu items: {len(menu)}")
    
    # Find all desserts
    print("\n" + "=" * 60)
    print("Finding all desserts in menu:")
    desserts = []
    
    for i, item in enumerate(menu):
        name = item.get('dish', '')
        desc = item.get('description', '').lower()
        subcat = item.get('subcategory', '').lower()
        
        # Check if it's a dessert
        if (subcat == 'dessert' or 
            any(d in name.lower() for d in ['tiramisu', 'cake', 'gelato', 'panna cotta', 'cheesecake']) or
            any(d in desc for d in ['dessert', 'sweet', 'chocolate', 'cream'])):
            desserts.append({
                'index': i,
                'name': name,
                'price': item.get('price'),
                'subcategory': item.get('subcategory')
            })
    
    print(f"\nFound {len(desserts)} desserts:")
    for d in desserts:
        print(f"  {d['index']}. {d['name']} ({d['price']}) - subcategory: {d['subcategory']}")
    
    # Find all seafood
    print("\n" + "=" * 60)
    print("Finding all seafood in menu:")
    seafood = []
    
    for i, item in enumerate(menu):
        name = item.get('dish', '')
        desc = item.get('description', '').lower()
        ingredients = ' '.join(str(x).lower() for x in item.get('ingredients', []))
        
        # Check if it's seafood
        seafood_keywords = ['seafood', 'fish', 'salmon', 'tuna', 'shrimp', 'lobster', 'crab', 'scallop', 'mussel', 'oyster', 'calamari', 'linguine']
        if any(s in name.lower() or s in desc or s in ingredients for s in seafood_keywords):
            seafood.append({
                'index': i,
                'name': name,
                'price': item.get('price'),
                'subcategory': item.get('subcategory')
            })
    
    print(f"\nFound {len(seafood)} seafood items:")
    for s in seafood:
        print(f"  {s['index']}. {s['name']} ({s['price']}) - subcategory: {s['subcategory']}")
        
else:
    print(f"Error: {response.status_code}")