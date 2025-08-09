#!/usr/bin/env python3
"""
Test what context is actually being built by the restaurant backend
"""
import requests
import uuid
import json

print("Testing Actual Restaurant Backend Context")
print("=" * 80)

# First, let's see what context format the restaurant is building
print("\n1. CHECKING MENU DATA FORMAT:")
response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")
if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    # Check first few items
    print(f"Total menu items: {len(menu)}")
    print("\nFirst 5 items structure:")
    for i, item in enumerate(menu[:5]):
        print(f"\n{i}. {item.get('dish', 'NO DISH')}")
        print(f"   Keys: {', '.join(item.keys())}")
        print(f"   Subcategory: {item.get('subcategory', 'NO SUBCAT')}")

# Test with a very specific query to see the response pattern
print("\n\n2. TESTING SPECIFIC QUERIES:")
test_queries = [
    "what pasta do you have",
    "list all pasta dishes", 
    "I want to see every pasta option",
    "show me ALL your pasta dishes, list them all",
    "give me the complete pasta menu"
]

for query in test_queries:
    print(f"\nQuery: '{query}'")
    
    response = requests.post(
        'https://restaurantchat-production.up.railway.app/chat',
        json={
            'restaurant_id': 'bella_vista_restaurant',
            'client_id': str(uuid.uuid4()),
            'sender_type': 'client',
            'message': query
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('answer', '')
        # Count items
        pasta_names = ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna', 'Minestrone']
        mentioned = [p for p in pasta_names if p in answer]
        print(f"  Response: {answer[:100]}...")
        print(f"  Items: {len(mentioned)} - {mentioned}")
    else:
        print(f"  Error: {response.status_code}")

# Let's check if the issue is with the context format
print("\n\n3. TESTING CONTEXT FORMAT HYPOTHESIS:")
print("The restaurant backend might be sending context in a different format than our tests.")

# Try to replicate what the restaurant backend sends
restaurant_style_prompt = """You are a friendly restaurant assistant helping customers with menu questions.

ABSOLUTE REQUIREMENT: When asked about any food category (pasta, pizza, salad, etc.), you MUST list EVERY SINGLE item from that category shown in the context below. Do not select "examples" or "some options" - list them ALL.

Restaurant: bella_vista_restaurant
Customer asks: 'what pasta do you have'

Relevant menu information:
Starter: Minestrone Soup ($8.99)
Main: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99), Penne Arrabbiata ($16.99), Seafood Linguine ($32.99), Gnocchi Gorgonzola ($19.99), Lasagna Bolognese ($20.99)

CRITICAL: You MUST list EVERY SINGLE item from the context above. Do not summarize, truncate, or give examples - list them ALL.

Customer: what pasta do you have
Assistant:"""

print("\nTesting with restaurant-style context (includes Minestrone):")
response = requests.post(
    "https://mia-backend-production.up.railway.app/api/generate",
    json={
        "prompt": restaurant_style_prompt,
        "max_tokens": 200,
        "temperature": 0.7,
        "source": "test"
    }
)

if response.status_code == 200:
    answer = response.json().get('text', '')
    print(f"Response: {answer}")
    mentioned = sum(1 for p in ['Minestrone', 'Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna'] if p in answer)
    print(f"Items mentioned: {mentioned}/7")