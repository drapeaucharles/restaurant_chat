#!/usr/bin/env python3
"""
Test improved pasta search logic
"""
import requests
import json

print("Testing improved pasta search logic")
print("=" * 60)

# Get restaurant data
restaurant_id = "bella_vista_restaurant"
response = requests.get(f"https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id={restaurant_id}")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    # Simulate the improved search logic
    query = "what pasta do you have"
    query_lower = query.lower()
    found_items = []
    
    # Search ALL menu items (no limit)
    for item in menu:
        name = item.get('name') or item.get('dish', '')
        if not name:
            continue
            
        name_lower = name.lower()
        description = item.get('description', '').lower()
        
        # Special handling for pasta queries
        if 'pasta' in query_lower:
            pasta_keywords = ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi', 'fettuccine', 'rigatoni', 'tagliatelle']
            if any(keyword in name_lower or keyword in description for keyword in pasta_keywords):
                price = item.get('price', '')
                found_items.append({
                    'name': name,
                    'price': price,
                    'category': item.get('subcategory', 'main')
                })
    
    print(f"Found {len(found_items)} pasta items with improved search:")
    
    # Group by category
    by_category = {}
    for item in found_items[:15]:  # Using the increased limit
        cat = item['category']
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(f"{item['name']} ({item['price']})")
    
    print("\nContext that will be sent to MIA:")
    for cat, items in by_category.items():
        print(f"{cat.title()}: {', '.join(items)}")
        
else:
    print(f"Error: {response.status_code}")