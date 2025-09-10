#!/usr/bin/env python3
"""
Final test to confirm the issue and potential fix
"""
import requests
import json
import uuid
import time

BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

print("Waiting for deployment...")
time.sleep(10)

# Test the problematic scenario
client_id = str(uuid.uuid4())

print("\n=== Setting shellfish allergy ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "I'm allergic to shellfish"
    },
    timeout=30
)
print(f"Response: {response.json().get('answer', '')[:80]}...")

print("\n=== Asking for seafood (triggers both tools) ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "What seafood options do you have? [DEBUG]"
    },
    timeout=30
)

if response.status_code == 200:
    answer = response.json().get('answer', '')
    
    if "[DEBUG INFO]" in answer:
        actual = answer[:answer.find("[DEBUG INFO]")].strip()
        debug_info = json.loads(answer[answer.find("[DEBUG INFO]") + 13:].strip())
        
        print(f"\nActual response: {actual[:150]}...")
        
        tools = [t.get('tool') for t in debug_info.get('phase1_tools_selected', [])]
        print(f"\nTools selected: {tools}")
        
        print("\nTool results:")
        for result in debug_info.get('tool_results_summary', []):
            print(f"  - {result.get('tool')}: {result.get('found')} items")
        
        # Check if fish are mentioned
        fish_mentioned = sum(1 for fish in ['salmon', 'sea bass', 'tuna'] if fish in actual.lower())
        print(f"\nFish mentioned in response: {fish_mentioned}")

# Alternative approach - ask for fish directly
print("\n\n=== Alternative: Ask for fish directly ===")
response = requests.post(
    f"{BASE_URL}/chat",
    json={
        "restaurant_id": RESTAURANT_ID,
        "client_id": client_id,
        "message": "Do you have any fish dishes that are safe for me?"
    },
    timeout=30
)

answer = response.json().get('answer', '')
print(f"Response: {answer[:200]}...")

fish_mentioned = sum(1 for fish in ['salmon', 'sea bass', 'tuna'] if fish in answer.lower())
print(f"Fish mentioned: {fish_mentioned}")

# Summary
print("\n\n=== SUMMARY ===")
print("The issue: When customer has shellfish allergy and asks for 'seafood',")
print("the system uses both shellfish-free filter AND seafood search.")
print("This results in 0 items even though we have 3 fish that are seafood and shellfish-free.")
print("\nWorkaround: Ask for 'fish' instead of 'seafood' when you have shellfish allergy.")