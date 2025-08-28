#!/usr/bin/env python3
"""
Test the broken logic
"""
import requests
import uuid

print("Testing broken chat logic")
print("=" * 80)

test_messages = [
    "hello how are you",
    "hi",
    "good morning",
    "what pasta do you have",
    "show me desserts",
    "thank you",
    "what's your name"
]

for message in test_messages:
    print(f"\nUser: '{message}'")
    
    response = requests.post(
        'https://restaurantchat-production.up.railway.app/chat',
        json={
            'restaurant_id': 'bella_vista_restaurant',
            'client_id': str(uuid.uuid4()),
            'sender_type': 'client',
            'message': message
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('answer', '')
        print(f"Bot: {answer[:150]}...")
        
        # Check if it's returning menu inappropriately
        if any(word in answer for word in ['Truffle', 'Caprese', 'menu', 'dishes']) and message in ['hello', 'hi', 'thank you']:
            print("❌ ERROR: Returning menu for a greeting/thanks!")
    else:
        print(f"Error: {response.status_code}")