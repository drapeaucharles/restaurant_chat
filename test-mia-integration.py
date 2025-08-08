#!/usr/bin/env python3
"""
Test script to verify MIA integration with Restaurant backend
"""
import requests
import json

# MIA Backend URL
MIA_BACKEND_URL = "https://mia-backend-production.up.railway.app"

print("Testing MIA Backend Integration")
print("=" * 50)

# Test 1: MIA Health Check
print("\n1. Testing MIA Health Check...")
try:
    response = requests.get(f"{MIA_BACKEND_URL}/health")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: MIA API Health Check
print("\n2. Testing MIA API Health Check...")
try:
    response = requests.get(f"{MIA_BACKEND_URL}/api/health")
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {response.json()}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: MIA Generate Endpoint
print("\n3. Testing MIA Generate Endpoint...")
try:
    test_prompt = {
        "prompt": "Hello, what are your restaurant hours?",
        "source": "test-script",
        "max_tokens": 150,
        "temperature": 0.7
    }
    response = requests.post(
        f"{MIA_BACKEND_URL}/api/generate",
        json=test_prompt,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status Code: {response.status_code}")
    print(f"   Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"   Error: {e}")

# Test 4: Test different prompts
print("\n4. Testing Different Prompts...")
test_prompts = [
    "What vegetarian options do you have?",
    "Do you have gluten-free menu items?",
    "¿Hablas español?",
    "Bonjour, avez-vous un menu français?"
]

for i, prompt in enumerate(test_prompts, 1):
    print(f"\n   Test {i}: {prompt}")
    try:
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json={"prompt": prompt, "source": "test"},
            headers={"Content-Type": "application/json"}
        )
        result = response.json()
        print(f"   Response: {result.get('text', 'No text in response')}")
        print(f"   Source: {result.get('source', 'Unknown')}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 50)
print("MIA Integration Test Complete!")