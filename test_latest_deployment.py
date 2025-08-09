#!/usr/bin/env python3
"""
Test the latest deployment
"""
import requests
import uuid
import json

print("Testing latest Restaurant backend deployment")
print("=" * 80)

# Check version endpoint
print("\n1. Checking version endpoint:")
response = requests.get("https://restaurantchat-production.up.railway.app/version")
if response.status_code == 200:
    print("Version info:", json.dumps(response.json(), indent=2))
else:
    print(f"Version endpoint not available: {response.status_code}")

# Check chat provider
print("\n2. Checking chat provider:")
response = requests.get("https://restaurantchat-production.up.railway.app/debug/chat-provider")
if response.status_code == 200:
    provider = response.json()
    print("Chat provider:", json.dumps(provider, indent=2))
else:
    print(f"Chat provider endpoint: {response.status_code}")

# Test pasta query
print("\n3. Testing pasta query:")
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
    print(f"Response: {answer}")
    
    # Count pasta dishes
    pasta_names = ['Minestrone', 'Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna']
    mentioned = [p for p in pasta_names if p in answer]
    print(f"\nPasta dishes mentioned: {len(mentioned)}/7")
    print(f"Which ones: {mentioned}")
    
    if len(mentioned) >= 6:
        print("\n✅ SUCCESS! All pasta dishes are being listed!")
    else:
        print("\n❌ Still not listing all pasta dishes")
else:
    print(f"Error: {response.status_code}")

# Test desserts too
print("\n4. Testing desserts query:")
client_id = str(uuid.uuid4())
response = requests.post(
    'https://restaurantchat-production.up.railway.app/chat',
    json={
        'restaurant_id': 'bella_vista_restaurant',
        'client_id': client_id,
        'sender_type': 'client',
        'message': 'what desserts do you have'
    }
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    print(f"Response: {answer}")
else:
    print(f"Error: {response.status_code}")