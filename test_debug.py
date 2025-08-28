#!/usr/bin/env python3
"""Test debug endpoints"""
import requests
import json
import uuid

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("Testing Debug Endpoints")
print("="*50)

# Test 1: Direct MIA test
print("\n1. Testing MIA directly...")
try:
    response = requests.get(f"{BASE_URL}/test-mia", timeout=15)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# Test 2: Debug endpoint
print("\n2. Testing debug endpoint...")
try:
    client_id = str(uuid.uuid4())
    response = requests.post(
        f"{BASE_URL}/debug?restaurant_id=bella_vista_restaurant&client_id={client_id}",
        json={
            "restaurant_id": "bella_vista_restaurant",
            "client_id": client_id,
            "sender_type": "client",
            "message": "What pasta do you have?"
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")

# Test 3: Regular chat with debug response
print("\n3. Testing regular chat...")
try:
    client_id = str(uuid.uuid4())
    response = requests.post(
        f"{BASE_URL}/chat/?restaurant_id=bella_vista_restaurant&client_id={client_id}",
        json={
            "restaurant_id": "bella_vista_restaurant",
            "client_id": client_id,
            "sender_type": "client",
            "message": "Hello!"
        },
        timeout=15
    )
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        answer = result.get("answer", "")
        print(f"Answer: {answer}")
        if answer.startswith("Debug:") or answer.startswith("Error:"):
            print("Got debug/error response - this helps diagnose the issue!")
    else:
        print(f"Error: {response.text}")
except Exception as e:
    print(f"Exception: {e}")