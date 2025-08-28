#!/usr/bin/env python3
"""Final test of enhanced chat service"""
import requests
import uuid
import json
import time

BASE_URL = "https://restaurantchat-production.up.railway.app"

def test_chat(message, test_name):
    """Test a chat message and show full response"""
    print(f"\n{'='*60}")
    print(f"Test: {test_name}")
    print(f"Message: {message}")
    
    client_id = str(uuid.uuid4())
    url = f"{BASE_URL}/chat/?restaurant_id=bella_vista_restaurant&client_id={client_id}"
    
    data = {
        "restaurant_id": "bella_vista_restaurant",
        "client_id": client_id,
        "sender_type": "client",
        "message": message
    }
    
    start_time = time.time()
    response = requests.post(url, json=data, timeout=30)
    elapsed = time.time() - start_time
    
    print(f"Status: {response.status_code}")
    print(f"Response time: {elapsed:.2f}s")
    
    if response.status_code == 200:
        result = response.json()
        answer = result.get("answer", "")
        
        print(f"\nAI Response:")
        print(answer if answer else "[Empty response]")
        
        # Quality checks
        if test_name == "Greeting":
            if answer and "menu" not in answer.lower()[:100]:
                print("\n✅ PASS: No menu in greeting")
            else:
                print("\n❌ FAIL: Menu appears in greeting or empty response")
                
        elif test_name == "Pasta Query":
            if answer:
                pasta_count = sum(1 for word in ["carbonara", "ravioli", "linguine", "penne", "gnocchi", "lasagna"] if word in answer.lower())
                price_count = answer.count("$")
                print(f"\nPasta items found: {pasta_count}")
                print(f"Prices shown: {price_count}")
                if pasta_count >= 4:
                    print("✅ PASS: Multiple pasta dishes listed")
                else:
                    print("❌ FAIL: Not enough pasta dishes")
            else:
                print("\n❌ FAIL: Empty response")
                
        elif test_name == "French Greeting":
            if answer and any(word in answer for word in ["Bonjour", "bienvenue", "plaisir", "Hello"]):
                print("\n✅ PASS: Appropriate greeting response")
            else:
                print("\n❌ FAIL: No greeting in response")
    else:
        print(f"Error response: {response.text}")
    
    return response.status_code == 200

def main():
    print("Enhanced Chat Service Test - Production")
    print("="*60)
    
    # Check health first
    health = requests.get(f"{BASE_URL}/health")
    if health.status_code == 200:
        print("Health check:", json.dumps(health.json(), indent=2))
    
    # Run tests
    tests = [
        ("Hello!", "Greeting"),
        ("What pasta dishes do you have?", "Pasta Query"),
        ("Bonjour!", "French Greeting"),
        ("What do you recommend?", "Recommendation")
    ]
    
    success_count = 0
    for message, test_name in tests:
        if test_chat(message, test_name):
            success_count += 1
        time.sleep(2)  # Avoid rate limiting
    
    print(f"\n{'='*60}")
    print(f"Tests passed: {success_count}/{len(tests)}")
    
    # Test caching by repeating first query
    print("\nTesting cache (repeating greeting)...")
    test_chat("Hello!", "Cache Test")

if __name__ == "__main__":
    main()