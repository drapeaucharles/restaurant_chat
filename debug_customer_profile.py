#!/usr/bin/env python3
"""
Debug if customer profile affects menu items
"""
import requests
import json
import uuid
import time

BASE_URL = "https://restaurantchat-production.up.railway.app"  
RESTAURANT_ID = "bella_vista_restaurant"

# Wait for deployment
time.sleep(5)

# Test with explicit request to use both tools
client_id = str(uuid.uuid4())

print("Setting shellfish allergy...")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "I'm allergic to shellfish"
    },
    timeout=30
)

print("\nForcing both tools with explicit request...")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "Please use the filter_shellfish_free tool and the search_by_food_type tool with food_type='Seafood' [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    
    if "[DEBUG INFO]" in answer:
        actual = answer[:answer.find("[DEBUG INFO]")].strip()
        debug_info = json.loads(answer[answer.find("[DEBUG INFO]") + 13:].strip())
        
        print(f"\nResponse: {actual[:150]}...")
        print(f"\nTools: {[t.get('tool') for t in debug_info.get('phase1_tools_selected', [])]}")
        
        # Check results
        for result in debug_info.get('tool_results_summary', []):
            print(f"{result.get('tool')}: {result.get('found')} items")