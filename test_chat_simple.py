#!/usr/bin/env python3
import requests
import json
import time
import uuid

# Test the chat API
BASE_URL = "https://restaurantchat-production.up.railway.app"

# Test queries
tests = [
    ("Hello!", "Greeting test"),
    ("What pasta dishes do you have?", "Pasta test"),
    ("Bonjour!", "French test")
]

print("Testing Restaurant Chat API")
print("=" * 50)

# First check the API status
print("\nChecking API status...")
status = requests.get(BASE_URL)
if status.status_code == 200:
    print(f"API is running: {status.json()}")
else:
    print(f"API error: {status.status_code}")

# Test each query
for message, description in tests:
    print(f"\n{description}: '{message}'")
    
    # Generate a valid UUID for client_id
    client_id = str(uuid.uuid4())
    
    # Try the correct endpoint with query params
    try:
        url = f"{BASE_URL}/chat?restaurant_id=bella_vista_restaurant&client_id={client_id}"
        data = {
            "restaurant_id": "bella_vista_restaurant", 
            "client_id": client_id, 
            "sender_type": "client", 
            "message": message
        }
        
        response = requests.post(url, json=data, timeout=10)
        
        print(f"  Status: {response.status_code}")
        if response.status_code == 200:
            answer = response.json().get("answer", "No answer")
            print(f"  Response: {answer[:200]}...")
            
            # Check quality indicators
            if message == "Hello!" and "menu" not in answer.lower()[:50]:
                print("  ✓ Good: No menu in greeting")
            elif "pasta" in message.lower() and answer.count("$") >= 5:
                print("  ✓ Good: Multiple pasta items listed")
            elif message == "Bonjour!" and any(fr in answer for fr in ["Bonjour", "bienvenue"]):
                print("  ✓ Good: French response")
        else:
            print(f"  Error: {response.text[:200]}")
    except Exception as e:
        print(f"  Exception: {e}")
    
    time.sleep(1)  # Be nice to the server

# Check for enhanced features
print("\n" + "="*50)
print("Checking for enhanced features...")
try:
    provider = requests.get(f"{BASE_URL}/chat/provider")
    if provider.status_code == 200:
        print("✓ Enhanced route active!")
        print(json.dumps(provider.json(), indent=2))
    else:
        print("✗ Enhanced route not found")
except:
    print("✗ Could not check enhanced route")