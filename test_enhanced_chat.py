#!/usr/bin/env python3
"""
Test script for enhanced MIA chat service
Tests all improvements:
- Query type detection
- Dynamic temperature
- Caching
- Multi-language support
- Enhanced prompts
"""
import requests
import time
import uuid
import json

# Configuration
BASE_URL = "http://localhost:8000"  # Update if needed
RESTAURANT_ID = "bella_vista_restaurant"

def test_query(message, description, client_id=None):
    """Test a single query and show results"""
    if not client_id:
        client_id = str(uuid.uuid4())
    
    print(f"\n{'='*60}")
    print(f"Test: {description}")
    print(f"Query: {message}")
    print(f"Client ID: {client_id}")
    
    start_time = time.time()
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "restaurant_id": RESTAURANT_ID,
            "client_id": client_id,
            "sender_type": "client",
            "message": message
        }
    )
    
    elapsed = time.time() - start_time
    
    if response.status_code == 200:
        answer = response.json().get("answer", "")
        print(f"Response Time: {elapsed:.2f}s")
        print(f"Response: {answer}")
        
        # Check if it was cached
        if elapsed < 0.5:
            print("✓ Likely cached response (fast)")
        
        return {
            "success": True,
            "response": answer,
            "time": elapsed,
            "client_id": client_id
        }
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return {"success": False, "error": response.text}

def test_conversation_flow():
    """Test conversation memory"""
    client_id = str(uuid.uuid4())
    print(f"\n{'='*60}")
    print("CONVERSATION FLOW TEST")
    
    # First message
    test_query("Hello!", "Greeting (conversation start)", client_id)
    time.sleep(1)
    
    # Follow-up
    test_query("What pasta do you have?", "Menu query (should remember greeting)", client_id)
    time.sleep(1)
    
    # Specific follow-up
    test_query("Tell me more about the carbonara", "Specific item (should have context)", client_id)

def main():
    print("Enhanced MIA Chat Service Test Suite")
    print("="*60)
    
    # Check provider info
    print("\nChecking chat provider configuration...")
    provider_resp = requests.get(f"{BASE_URL}/chat/provider")
    if provider_resp.status_code == 200:
        print(f"Provider Info: {json.dumps(provider_resp.json(), indent=2)}")
    
    # Test different query types
    tests = [
        # Greetings - should be warm, no menu listing
        ("Hello!", "Greeting in English"),
        ("Bonjour!", "Greeting in French"),
        ("¡Hola!", "Greeting in Spanish"),
        
        # Menu queries - should list items with prices
        ("What's on your menu?", "General menu query"),
        ("What pasta do you have?", "Specific category query"),
        ("Show me your desserts", "Dessert category query"),
        
        # Specific items - detailed info
        ("Tell me about the lobster ravioli", "Specific item query"),
        ("How much is the tiramisu?", "Price query"),
        
        # Recommendations - should be enthusiastic
        ("What do you recommend?", "General recommendation"),
        ("What's your best pasta?", "Category recommendation"),
        
        # Dietary queries - filtered results
        ("Do you have vegetarian options?", "Dietary query"),
        ("What gluten-free dishes do you have?", "Allergen query"),
        
        # Hours/Contact
        ("What are your hours?", "Hours query"),
        ("When do you close?", "Closing time query"),
    ]
    
    print("\n" + "="*60)
    print("INDIVIDUAL QUERY TESTS")
    
    for message, description in tests:
        result = test_query(message, description)
        time.sleep(1)  # Avoid rate limiting
    
    # Test caching - same query twice
    print("\n" + "="*60)
    print("CACHE TEST")
    
    cache_test_query = "What are your most popular dishes?"
    result1 = test_query(cache_test_query, "First query (not cached)")
    time.sleep(0.5)
    result2 = test_query(cache_test_query, "Same query (should be cached)")
    
    if result1["success"] and result2["success"]:
        if result2["time"] < result1["time"] * 0.1:  # 10x faster
            print("✓ Cache is working! Second query was much faster")
        else:
            print("⚠ Cache might not be working properly")
    
    # Test conversation flow
    test_conversation_flow()
    
    # Cache stats
    print("\n" + "="*60)
    print("CACHE STATISTICS")
    cache_stats = requests.get(f"{BASE_URL}/chat/cache/stats")
    if cache_stats.status_code == 200:
        print(json.dumps(cache_stats.json(), indent=2))
    
    print("\n" + "="*60)
    print("Test suite completed!")

if __name__ == "__main__":
    main()