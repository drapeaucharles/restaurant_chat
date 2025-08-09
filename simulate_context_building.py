#!/usr/bin/env python3
"""
Simulate the exact context building logic
"""
import requests

# Get restaurant data
response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")

if response.status_code == 200:
    data = response.json()
    menu_items = data.get('menu', [])
    
    query = "what pasta do you have"
    query_lower = query.lower()
    
    print(f"Simulating context building for: '{query}'")
    print("=" * 80)
    
    found_items = []
    
    # Search ALL menu items - matching the production code
    for idx, item in enumerate(menu_items):
        name = item.get('name') or item.get('dish', '')
        if not name:
            continue
            
        name_lower = name.lower()
        ingredients = item.get('ingredients', [])
        description = item.get('description', '').lower()
        
        # Check relevance - matching production code
        relevant = False
        
        # Special handling for pasta queries
        if 'pasta' in query_lower:
            pasta_keywords = ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi', 'fettuccine', 'rigatoni', 'tagliatelle']
            # Check name, description AND ingredients for pasta keywords
            item_text = f"{name_lower} {description} {' '.join(str(i).lower() for i in ingredients)}"
            if any(keyword in item_text for keyword in pasta_keywords):
                relevant = True
                print(f"Found pasta at index {idx}: {name}")
        
        if relevant:
            price = item.get('price', '')
            desc = item.get('description', '')[:80]
            found_items.append({
                'name': name,
                'price': price,
                'desc': desc,
                'category': item.get('subcategory', 'main')
            })
    
    print(f"\nTotal found: {len(found_items)}")
    
    # Format as context
    context_lines = []
    if found_items:
        # Group by category
        by_category = {}
        for item in found_items:  # No limit for pasta
            cat = item['category']
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(f"{item['name']} ({item['price']})")
        
        for cat, items in by_category.items():
            context_lines.append(f"{cat.title()}: {', '.join(items)}")
    
    print("\nContext that would be built:")
    print("-" * 80)
    for line in context_lines:
        print(line)
        
else:
    print(f"Error: {response.status_code}")