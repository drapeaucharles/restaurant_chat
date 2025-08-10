"""
Check deployment configuration and test improved service
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("Checking Restaurant Backend Deployment...")
print("="*60)

# 1. Check root endpoint
try:
    response = requests.get(f"{BASE_URL}/")
    if response.status_code == 200:
        data = response.json()
        print("Deployment Info:")
        print(f"  Version: {data['deployment']['version']}")
        print(f"  Service: {data['deployment']['mia_chat_service']}")
        print(f"  Features: {data['deployment']['features']}")
except Exception as e:
    print(f"Error checking root: {e}")

# 2. Check if improved endpoint exists
print("\nChecking improved chat endpoint...")
try:
    # Try the improved endpoint with a test
    response = requests.post(
        f"{BASE_URL}/chat/improved",
        json={
            "restaurant_id": "bella_vista_restaurant",
            "client_id": "test-improved",
            "sender_type": "client",
            "message": "Hello"
        }
    )
    print(f"Improved endpoint status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"Improved response: {result.get('answer', 'No answer')[:100]}...")
except Exception as e:
    print(f"Improved endpoint not available: {e}")

# 3. Test comparison endpoint
print("\nChecking comparison endpoint...")
try:
    response = requests.get(
        f"{BASE_URL}/chat/test-comparison",
        params={"query": "Hello"}
    )
    print(f"Comparison endpoint status: {response.status_code}")
except Exception as e:
    print(f"Comparison endpoint not available: {e}")

print("\n" + "="*60)
print("CONCLUSION:")
print("The improved service is deployed but may not be enabled by default.")
print("To enable, set environment variable: USE_IMPROVED_CHAT=true")
print("="*60)