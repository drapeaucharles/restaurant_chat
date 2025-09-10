#!/usr/bin/env python3
"""
Debug why filter returns 0 items
"""
import requests
import json
import uuid

BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

# Test WITHOUT setting allergy first
client_id = str(uuid.uuid4())

print("=== Test 1: Shellfish-free filter WITHOUT allergy set ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "Show me all shellfish-free options [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    if "[DEBUG INFO]" in answer:
        debug_start = answer.find("[DEBUG INFO]") + 13
        debug_info = json.loads(answer[debug_start:].strip())
        
        for result in debug_info.get('tool_results_summary', []):
            if result.get('tool') == 'filter_shellfish_free':
                print(f"Shellfish-free filter found: {result.get('found', 0)} items")
        
        # Check response
        actual = answer[:answer.find("[DEBUG INFO]")].strip()
        if 'salmon' in actual.lower():
            print("✅ Response includes fish items")
        else:
            print("❌ Response doesn't include fish items")

# Test WITH allergy set
print("\n=== Test 2: Shellfish-free filter WITH allergy set ===")
client_id2 = str(uuid.uuid4())

# Set allergy
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id2,
        "message": "I have a shellfish allergy"
    },
    timeout=30
)

# Now use filter
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id2,
        "message": "Show me all shellfish-free dishes [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    if "[DEBUG INFO]" in answer:
        debug_start = answer.find("[DEBUG INFO]") + 13
        debug_info = json.loads(answer[debug_start:].strip())
        
        for result in debug_info.get('tool_results_summary', []):
            if result.get('tool') == 'filter_shellfish_free':
                print(f"Shellfish-free filter found: {result.get('found', 0)} items")