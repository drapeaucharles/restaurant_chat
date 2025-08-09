#!/usr/bin/env python3
"""
Test pasta query in production to see actual context
"""
import requests
import json
import time

print("Testing pasta query in production")
print("=" * 60)

# Test the actual chat endpoint
client_id = f"test-pasta-{int(time.time())}"
response = requests.post(
    'https://restaurantchat-production.up.railway.app/chat',
    json={
        'restaurant_id': 'bella_vista_restaurant',
        'client_id': client_id,
        'sender_type': 'client',
        'message': 'what pasta do you have'
    },
    headers={'Content-Type': 'application/json'}
)

print(f"Response status: {response.status_code}")
if response.status_code == 200:
    result = response.json()
    print(f"\nAnswer: {result.get('answer')}")
else:
    print(f"Error: {response.text}")

# Also test a direct context check
print("\n" + "=" * 60)
print("Checking what context is being built...")

# Get restaurant data to see menu structure
info_response = requests.get(
    f"https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant"
)

if info_response.status_code == 200:
    data = info_response.json()
    menu = data.get('menu', [])
    
    # Count pasta dishes
    pasta_count = 0
    pasta_items = []
    for item in menu:
        name = (item.get('name') or item.get('dish', '')).lower()
        desc = item.get('description', '').lower()
        
        # Check if it's pasta
        pasta_keywords = ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']
        if any(k in name or k in desc for k in pasta_keywords):
            pasta_count += 1
            pasta_items.append(item.get('name') or item.get('dish'))
            
    print(f"\nTotal pasta dishes found in menu: {pasta_count}")
    print(f"Pasta items: {pasta_items}")