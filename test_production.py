#!/usr/bin/env python3
"""Test the production deployment"""
import requests
import json
import uuid

# Production URL
BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

def test_chat(message, description):
    """Test a chat message"""
    print(f"\n{description}")
    print(f"Query: {message}")
    
    # Try the correct endpoint with query params
    client_id = str(uuid.uuid4())
    response = requests.post(
        f"{BASE_URL}/chat?restaurant_id={RESTAURANT_ID}&client_id={client_id}",
        json={
            "restaurant_id": RESTAURANT_ID,
            "client_id": client_id,
            "sender_type": "client",
            "message": message
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"Response: {result.get('answer', 'No answer')}")
        return result.get('answer', '')
    else:
        print(f"Error {response.status_code}: {response.text}")
        return None

def main():
    print("Testing Restaurant Chat Production Deployment")
    print("=" * 50)
    
    # Test different queries
    tests = [
        ("Hello!", "Testing greeting (should be warm, no menu)"),
        ("What pasta do you have?", "Testing pasta query (should list ALL pasta)"),
        ("Bonjour!", "Testing French greeting"),
        ("What do you recommend?", "Testing recommendation")
    ]
    
    for message, description in tests:
        response = test_chat(message, description)
        if response:
            # Check if response quality improved
            if message == "Hello!" and "menu" not in response.lower():
                print("✓ Good: Greeting doesn't contain menu")
            elif "pasta" in message.lower() and response.count("$") > 5:
                print("✓ Good: Multiple pasta items with prices")
            elif message == "Bonjour!" and any(word in response for word in ["Bonjour", "bienvenue", "plaisir"]):
                print("✓ Good: French response detected")
    
    # Check if enhanced route exists
    print("\nChecking for enhanced features...")
    provider_resp = requests.get(f"{BASE_URL}/chat/provider")
    if provider_resp.status_code == 200:
        print("✓ Enhanced route is active!")
        print(json.dumps(provider_resp.json(), indent=2))
    else:
        print("✗ Enhanced route not found (might not be deployed yet)")

if __name__ == "__main__":
    main()