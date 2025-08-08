#!/usr/bin/env python3
"""
Test script to verify context improvements
"""
import requests
import json
import time
import uuid

RESTAURANT_URL = "https://restaurantchat-production.up.railway.app"
restaurant_id = "bella_vista_restaurant"

print("Testing Context Improvements")
print("=" * 60)

# Test queries that should now work better
test_queries = [
    {
        "query": "What vegetarian dishes do you have?",
        "expected": "Should list multiple vegetarian options with descriptions"
    },
    {
        "query": "Show me your starters",
        "expected": "Should list starter dishes with prices"
    },
    {
        "query": "Do you have gluten free options?",
        "expected": "Should list gluten-free dishes"
    },
    {
        "query": "What's on your menu?",
        "expected": "Should provide menu overview by category"
    },
    {
        "query": "Tell me about the seafood linguine",
        "expected": "Should describe specific dish with ingredients"
    },
    {
        "query": "What are your hours?",
        "expected": "Should show opening hours for each day"
    }
]

# Use same client ID for conversation continuity
client_id = str(uuid.uuid4())

for i, test in enumerate(test_queries, 1):
    print(f"\nTest {i}: {test['query']}")
    print(f"Expected: {test['expected']}")
    print("-" * 40)
    
    start_time = time.time()
    
    try:
        response = requests.post(
            f"{RESTAURANT_URL}/chat",
            json={
                "message": test['query'],
                "restaurant_id": restaurant_id,
                "client_id": client_id,
                "sender_type": "client"
            },
            headers={"Content-Type": "application/json"},
            timeout=30
        )
        
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'No answer')
            
            # Show first 200 chars of response
            if len(answer) > 200:
                print(f"Response: {answer[:200]}...")
            else:
                print(f"Response: {answer}")
            
            print(f"Response time: {elapsed:.2f}s")
            
            # Check if response seems contextual
            if any(word in answer.lower() for word in ['hello', 'welcome', 'help you today']):
                print("⚠️  WARNING: Generic response detected")
            else:
                print("✅ Contextual response")
                
        else:
            print(f"ERROR: HTTP {response.status_code}")
            print(response.text[:200])
            
    except Exception as e:
        print(f"ERROR: {e}")
    
    # Small delay between requests
    time.sleep(1)

print("\n" + "=" * 60)
print("Performance Summary:")
print("- All queries should return contextual responses")
print("- Response times should be under 10 seconds")
print("- No generic 'Hello! Welcome' responses expected")
print("\nNote: Results depend on restaurant backend deployment completing")