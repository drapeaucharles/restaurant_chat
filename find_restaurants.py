#!/usr/bin/env python3
"""Find available restaurants via API"""
import requests

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

# Try to get provider info first
try:
    response = requests.get(f"{BACKEND_URL}/chat/provider")
    if response.status_code == 200:
        print("✅ Backend is running!")
        print(f"Provider info: {response.json()}")
    else:
        print(f"❌ Provider endpoint error: {response.status_code}")
except Exception as e:
    print(f"❌ Connection error: {e}")

# Try a known restaurant ID (from previous tests)
test_restaurant_id = "b3a2f1d6-8e4c-4a9b-9c7e-2d3f4e5a6b7c"  # Generic test ID
print(f"\nTrying restaurant ID: {test_restaurant_id}")

try:
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={
            "restaurant_id": test_restaurant_id,
            "client_id": "550e8400-e29b-41d4-a716-446655440000",  # Valid UUID
            "message": "Hello",
            "sender_type": "customer"
        }
    )
    print(f"Response: {response.status_code} - {response.text[:200]}")
except Exception as e:
    print(f"Error: {e}")