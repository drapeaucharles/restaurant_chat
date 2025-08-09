#!/usr/bin/env python3
"""
Test pasta query in production with proper UUID
"""
import requests
import json
import uuid

print("Testing pasta query in production with proper UUID")
print("=" * 60)

# Test the actual chat endpoint with valid UUID
client_id = str(uuid.uuid4())
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
    answer = result.get('answer', '')
    print(f"\nAnswer: {answer}")
    
    # Count how many pasta dishes are mentioned
    pasta_keywords = ['Spaghetti', 'Linguine', 'Penne', 'Ravioli', 'Lasagna', 'Gnocchi', 'Minestrone']
    mentioned = [k for k in pasta_keywords if k in answer]
    print(f"\nPasta dishes mentioned: {len(mentioned)}")
    print(f"Which ones: {mentioned}")
else:
    print(f"Error: {response.text}")