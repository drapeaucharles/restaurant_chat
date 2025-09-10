#!/usr/bin/env python3
"""
Verify that seafood search filters out fish when customer has shellfish allergy
"""
import requests
import json
import uuid

BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

# Test 1: Seafood search WITHOUT allergy
print("=== Test 1: Seafood search (no allergy) ===")
client_id1 = str(uuid.uuid4())
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id1,
        "message": "Show me all seafood [DEBUG]"
    },
    timeout=30
)

if "[DEBUG INFO]" in response.json().get('answer', ''):
    answer = response.json()['answer']
    actual = answer[:answer.find("[DEBUG INFO]")]
    debug_info = json.loads(answer[answer.find("[DEBUG INFO]") + 13:].strip())
    
    for result in debug_info.get('tool_results_summary', []):
        if result.get('tool') == 'search_by_food_type':
            print(f"Seafood without allergy: {result.get('found')} items")
    
    # Check what's mentioned
    if 'salmon' in actual.lower():
        print("✅ Salmon mentioned")
    if 'lobster' in actual.lower():
        print("✅ Lobster mentioned")

# Test 2: Same search WITH shellfish allergy
print("\n=== Test 2: Seafood search (with shellfish allergy) ===")
client_id2 = str(uuid.uuid4())

# Set allergy
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id2,
        "message": "I'm allergic to shellfish"
    },
    timeout=30
)

# Search seafood
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id2,
        "message": "Show me all seafood [DEBUG]"
    },
    timeout=30
)

if "[DEBUG INFO]" in response.json().get('answer', ''):
    answer = response.json()['answer']
    actual = answer[:answer.find("[DEBUG INFO]")]
    debug_info = json.loads(answer[answer.find("[DEBUG INFO]") + 13:].strip())
    
    tools = [t.get('tool') for t in debug_info.get('phase1_tools_selected', [])]
    print(f"Tools used: {tools}")
    
    for result in debug_info.get('tool_results_summary', []):
        print(f"  - {result.get('tool')}: {result.get('found')} items")
    
    print(f"\nResponse: {actual[:150]}...")