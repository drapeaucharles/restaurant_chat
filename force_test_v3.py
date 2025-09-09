#!/usr/bin/env python3
"""Force test with a restaurant that has no rag_mode set to test DEFAULT_RAG_MODE"""
import requests
import uuid
import time

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

# Test with different restaurant IDs to see if any use V3
test_ids = [
    "admin",  # This might not have rag_mode set
    "admin@admin.com",  # This might not have rag_mode set
    "RestoBulla",  # Another restaurant
]

print("🧪 Testing different restaurants to find V3\n")

for restaurant_id in test_ids:
    print(f"\nTesting with restaurant: {restaurant_id}")
    
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={
            "restaurant_id": restaurant_id,
            "client_id": str(uuid.uuid4()),
            "message": "Hi there",
            "sender_type": "customer"
        },
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get('answer', '')
        
        if "[DEBUG:" in answer:
            print("  ❌ Has DEBUG output (not V3)")
        else:
            print("  ✅ NO DEBUG output (could be V3!)")
            print(f"  Response: {answer[:100]}...")
    else:
        print(f"  Error: {response.status_code}")

print("\n" + "="*60)
print("Testing with a non-existent restaurant (should use DEFAULT_RAG_MODE):")
fake_id = str(uuid.uuid4())
response = requests.post(
    f"{BACKEND_URL}/chat",
    json={
        "restaurant_id": fake_id,
        "client_id": str(uuid.uuid4()),
        "message": "Tell me about the pasta",
        "sender_type": "customer"
    }
)
print(f"Status: {response.status_code}")
if response.status_code == 404:
    print("Got 404 - Restaurant not found (expected)")
else:
    print(f"Response: {response.text[:200]}")