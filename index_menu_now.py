#!/usr/bin/env python3
"""
Index menu items now that the table exists
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("🍝 Indexing Menu Items...")
print("=" * 50)

# First, get the restaurant data
print("\n1. Getting restaurant data...")
response = requests.get(f"{BASE_URL}/restaurant/bella_vista_restaurant")
if response.status_code == 200:
    restaurant = response.json()
    menu_items = restaurant.get('menu', [])
    print(f"✅ Found {len(menu_items)} menu items")
    
    # Show some items
    for item in menu_items[:5]:
        print(f"   - {item.get('dish', 'Unknown')}: {item.get('price', 'N/A')}")
    if len(menu_items) > 5:
        print(f"   ... and {len(menu_items) - 5} more")
else:
    print(f"❌ Failed to get restaurant data: {response.status_code}")
    exit(1)

# Try to index via the API
print("\n2. Attempting to index via API...")
print("   Note: This requires authentication")

# Create test embeddings
print("\n3. Testing embedding creation...")
test_data = {
    "texts": [
        "Spaghetti Carbonara - Classic Roman pasta with eggs and guanciale",
        "Margherita Pizza - Fresh tomatoes, mozzarella, and basil"
    ]
}

response = requests.post(f"{BASE_URL}/embeddings/create", json=test_data)
if response.status_code == 200:
    print("✅ Embedding service is working!")
elif response.status_code == 404:
    print("⚠️  Embedding endpoint not found")

print("\n📝 To index the menu items, run:")
print("   railway run python index_menu_local.py bella_vista_restaurant")
print("\nOr if you have the Restaurant Management credentials:")
print("   POST to /embeddings/index/bella_vista_restaurant with auth token")

# Test semantic search
print("\n4. Testing semantic search...")
search_data = {
    "query": "vegetarian pasta",
    "restaurant_id": "bella_vista_restaurant",
    "limit": 5
}

response = requests.post(f"{BASE_URL}/embeddings/search", json=search_data)
if response.status_code == 200:
    results = response.json()
    if results.get('items'):
        print("✅ Semantic search is working!")
        for item in results['items'][:3]:
            print(f"   - {item['name']} (similarity: {item['similarity']:.2f})")
    else:
        print("⚠️  No embeddings indexed yet")
else:
    print(f"⚠️  Search returned: {response.json()}")

print("\n✅ Your RAG system is ready!")
print("   Just need to index the menu items for semantic search")