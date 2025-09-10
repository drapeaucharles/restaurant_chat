#!/usr/bin/env python3
"""
Debug the exact intersection flow
"""
import requests
import json
import uuid
import time

BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

# Wait for deployment
time.sleep(2)

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

# Test with specific prompt that should trigger both tools
print("Testing with explicit filter + search request...")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "Use the shellfish-free filter and seafood search to find options [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    
    if "[DEBUG INFO]" in answer:
        actual_end = answer.find("[DEBUG INFO]")
        actual = answer[:actual_end].strip()
        debug_json = answer[actual_end + 13:].strip()
        
        print(f"\nActual response: {actual[:200]}...")
        
        debug_info = json.loads(debug_json)
        print(f"\nTools used: {[t.get('tool') for t in debug_info.get('phase1_tools_selected', [])]}")
        
        # Check tool results in detail
        for result in debug_info.get('tool_results_summary', []):
            tool = result.get('tool')
            found = result.get('found')
            items_found = result.get('items_found')
            print(f"\n{tool}:")
            print(f"  - found field: {found}")
            print(f"  - items_found field: {items_found}")
        
        # Check phase 2 context
        if 'phase2_context' in debug_info:
            context = debug_info['phase2_context']
            # Count item mentions in context
            print(f"\nPhase 2 context length: {len(context)}")
            print("Looking for items in context...")
            
            # Check if specific items are mentioned
            items_to_check = ['Grilled Salmon', 'Sea Bass', 'Tuna Steak', 'no dishes', 'no items', 'empty']
            for item in items_to_check:
                if item.lower() in context.lower():
                    print(f"  - Found '{item}' in context")

# Test without customer allergy set
print("\n\n=== Test without allergy set ===")
client_id2 = str(uuid.uuid4())
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id2,
        "message": "Show me shellfish-free seafood options [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    if "[DEBUG INFO]" in answer:
        actual = answer[:answer.find("[DEBUG INFO]")].strip()
        print(f"\nWithout allergy set: {actual[:150]}...")
        
        # Check if fish are mentioned
        if 'salmon' in actual.lower() or 'sea bass' in actual.lower():
            print("✅ Fish items are mentioned!")
        else:
            print("❌ Fish items NOT mentioned")