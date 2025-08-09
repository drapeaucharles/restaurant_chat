#!/usr/bin/env python3
"""
Test the newly deployed code
"""
import requests
import uuid
import time

print("Testing newly deployed Restaurant backend")
print("=" * 80)

# Check deployment info
print("\n1. Deployment info:")
response = requests.get("https://restaurantchat-production.up.railway.app/")
if response.status_code == 200:
    deployment = response.json().get('deployment', {})
    print(f"  Version: {deployment.get('version')}")
    print(f"  Has pasta fixes: {deployment.get('has_pasta_fixes')}")
    print(f"  Timestamp: {deployment.get('deployment_timestamp')}")

# Test pasta query multiple times
print("\n2. Testing pasta query (3 attempts):")
for i in range(3):
    print(f"\n  Attempt {i+1}:")
    client_id = str(uuid.uuid4())
    
    response = requests.post(
        'https://restaurantchat-production.up.railway.app/chat',
        json={
            'restaurant_id': 'bella_vista_restaurant',
            'client_id': client_id,
            'sender_type': 'client',
            'message': 'what pasta do you have'
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('answer', '')
        print(f"    Response: {answer}")
        
        # Count pasta dishes
        pasta_names = ['Minestrone', 'Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna']
        mentioned = [p for p in pasta_names if p in answer]
        print(f"    Mentioned: {len(mentioned)}/7 - {mentioned}")
    else:
        print(f"    Error: {response.status_code}")
    
    time.sleep(1)

# Test other categories
print("\n3. Testing other food categories:")
test_queries = [
    "what desserts do you have",
    "show me your salads",
    "what seafood options do you have"
]

for query in test_queries:
    print(f"\n  Query: '{query}'")
    client_id = str(uuid.uuid4())
    
    response = requests.post(
        'https://restaurantchat-production.up.railway.app/chat',
        json={
            'restaurant_id': 'bella_vista_restaurant',
            'client_id': client_id,
            'sender_type': 'client',
            'message': query
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('answer', '')
        print(f"    Response: {answer[:100]}...")
    else:
        print(f"    Error: {response.status_code}")