#!/usr/bin/env python3
"""
Final test of pasta query
"""
import requests
import uuid
import time

print("Testing pasta query after all fixes...")
print("=" * 60)

# Test multiple times to see if consistent
for i in range(3):
    print(f"\nAttempt {i+1}:")
    
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
        
        # Count pasta dishes mentioned
        pasta_names = ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna', 'Minestrone']
        mentioned = [p for p in pasta_names if p in answer]
        print(f"Mentioned: {len(mentioned)} dishes - {mentioned}")
    else:
        print(f"Error: {response.status_code}")
    
    time.sleep(2)