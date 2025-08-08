#!/usr/bin/env python3
"""
Test script to verify Restaurant chat with MIA integration
Uses actual restaurant ID from the logs
"""
import requests
import json
import uuid

# Restaurant Backend URL
RESTAURANT_URL = "https://restaurantchat-production.up.railway.app"

print("Testing Restaurant Chat with MIA Integration")
print("=" * 50)

# Using the restaurant ID we see in the logs
restaurant_id = "bella_vista_restaurant"
client_id = str(uuid.uuid4())

print(f"\nUsing restaurant ID: {restaurant_id}")
print(f"Using client ID: {client_id}")

# Test 1: Check Restaurant Info
print("\n1. Checking Restaurant Info...")
try:
    response = requests.get(f"{RESTAURANT_URL}/restaurant/info?restaurant_id={restaurant_id}")
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        info = response.json()
        print(f"   Restaurant Name: {info.get('name', 'Unknown')}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: Send Chat Message
print("\n2. Sending Chat Message...")
chat_request = {
    "message": "Hello, what are your restaurant hours?",
    "restaurant_id": restaurant_id,
    "client_id": client_id,
    "sender_type": "client"
}

try:
    response = requests.post(
        f"{RESTAURANT_URL}/chat",
        json=chat_request,
        headers={"Content-Type": "application/json"}
    )
    print(f"   Status Code: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"   AI Response: {result.get('answer', 'No answer in response')}")
    else:
        print(f"   Error Response: {response.text}")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Try Different Questions
print("\n3. Testing Different Questions...")
test_questions = [
    "What vegetarian dishes do you have?",
    "Do you have a kids menu?",
    "What are your most popular dishes?"
]

for i, question in enumerate(test_questions, 1):
    print(f"\n   Question {i}: {question}")
    chat_request["message"] = question
    
    try:
        response = requests.post(
            f"{RESTAURANT_URL}/chat",
            json=chat_request,
            headers={"Content-Type": "application/json"}
        )
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', 'No answer')
            print(f"   Response: {answer[:100]}..." if len(answer) > 100 else f"   Response: {answer}")
        else:
            print(f"   Error: {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")

print("\n" + "=" * 50)
print("Restaurant Chat Test Complete!")