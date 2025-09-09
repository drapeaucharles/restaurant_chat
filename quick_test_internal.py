#!/usr/bin/env python3
"""Quick test of internal tools"""

import requests
import time

print("🧪 Quick Test - Internal Tools")
print("="*40)

# Simple test message
test_message = "What's in the Truffle Arancinidsa?"

print(f"Sending: {test_message}")
start = time.time()

try:
    response = requests.post(
        "https://restaurantchat-production.up.railway.app/chat",
        json={
            "restaurant_id": "bella_vista_restaurant",
            "client_id": "550e8400-e29b-41d4-a716-446655440002",
            "message": test_message,
            "language": "en"
        },
        timeout=15
    )
    
    elapsed = time.time() - start
    
    if response.status_code == 200:
        result = response.json()
        answer = result.get('answer', '')
        print(f"\n✅ Got response in {elapsed:.2f}s:")
        print(f"\nAnswer: {answer}")
        
        # Check quality
        has_ingredients = any(word in answer.lower() for word in ['arborio', 'truffle', 'parmesan', 'ingredients'])
        has_price = '$' in answer
        no_checking = 'let me check' not in answer.lower()
        
        print(f"\nQuality:")
        print(f"  Has ingredients: {'✅' if has_ingredients else '❌'}")
        print(f"  Has price: {'✅' if has_price else '❌'}")  
        print(f"  Direct answer: {'✅' if no_checking else '❌'}")
    else:
        print(f"\n❌ Error {response.status_code}: {response.text}")
        
except Exception as e:
    print(f"\n❌ Exception: {e}")