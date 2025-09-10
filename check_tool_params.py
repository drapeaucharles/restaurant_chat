#!/usr/bin/env python3
"""
Check exact tool parameters being sent
"""
import requests
import json
import uuid
import time

BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

# Wait for latest deployment  
time.sleep(5)

client_id = str(uuid.uuid4())

# Set allergy
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "I'm allergic to shellfish"
    },
    timeout=30
)

# Ask for seafood
print("Asking for seafood with shellfish allergy...")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "What seafood dishes do you have? [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    
    if "[DEBUG INFO]" in answer:
        debug_info = json.loads(answer[answer.find("[DEBUG INFO]") + 13:].strip())
        
        print("\n=== Phase 1 Tool Selection ===")
        for tool in debug_info.get('phase1_tools_selected', []):
            print(f"\nTool: {tool.get('tool')}")
            params = tool.get('params', tool.get('parameters', {}))
            print(f"Parameters: {json.dumps(params, indent=2)}")
        
        print("\n=== Tool Results Summary ===")
        for result in debug_info.get('tool_results_summary', []):
            print(f"{result.get('tool')}: {result.get('found')} items")

# Also test without allergy
print("\n\n=== Same question without allergy ===")
client_id2 = str(uuid.uuid4())

response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id2,
        "message": "What seafood dishes do you have? [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    
    if "[DEBUG INFO]" in answer:
        debug_info = json.loads(answer[answer.find("[DEBUG INFO]") + 13:].strip())
        
        for tool in debug_info.get('phase1_tools_selected', []):
            if tool.get('tool') == 'search_by_food_type':
                params = tool.get('params', tool.get('parameters', {}))
                print(f"Seafood search params (no allergy): {params}")
                
        for result in debug_info.get('tool_results_summary', []):
            if result.get('tool') == 'search_by_food_type':
                print(f"Result: {result.get('found')} items")