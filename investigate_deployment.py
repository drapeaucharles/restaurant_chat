#!/usr/bin/env python3
"""
Comprehensive investigation of deployment issues
"""
import requests
import uuid
import json
import time

print("=== DEPLOYMENT INVESTIGATION ===")
print("=" * 80)

# 1. Check deployment status
print("\n1. DEPLOYMENT STATUS:")
response = requests.get("https://restaurantchat-production.up.railway.app/")
if response.status_code == 200:
    data = response.json()
    deployment = data.get('deployment', {})
    print(f"   Version: {deployment.get('version')}")
    print(f"   Has pasta fixes: {deployment.get('has_pasta_fixes')}")
    print(f"   Branch: {deployment.get('branch')}")
    print(f"   Commit: {deployment.get('commit')}")

# 2. Check code version
print("\n2. CODE VERSION CHECK:")
response = requests.get("https://restaurantchat-production.up.railway.app/debug/code-version")
if response.status_code == 200:
    code_info = response.json()
    print(f"   Has v3 fixes: {code_info.get('has_v3_fixes')}")
    print(f"   System prompt preview: {code_info.get('system_prompt_preview')[:50]}...")
else:
    print(f"   Debug endpoint not available: {response.status_code}")

# 3. Check chat provider
print("\n3. CHAT PROVIDER:")
response = requests.get("https://restaurantchat-production.up.railway.app/debug/chat-provider")
if response.status_code == 200:
    provider_info = response.json()
    print(f"   Provider: {json.dumps(provider_info, indent=3)}")
else:
    print(f"   Provider endpoint not available: {response.status_code}")

# 4. Test different query variations
print("\n4. TESTING QUERY VARIATIONS:")
test_queries = [
    "what pasta do you have",
    "list all pasta dishes",
    "show me all your pasta options",
    "give me all your pasta choices",
    "pasta",
    "I want pasta what do you have"
]

for query in test_queries:
    print(f"\n   Query: '{query}'")
    client_id = str(uuid.uuid4())
    
    response = requests.post(
        'https://restaurantchat-production.up.railway.app/chat',
        json={
            'restaurant_id': 'bella_vista_restaurant',
            'client_id': client_id,
            'sender_type': 'client',
            'message': query
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('answer', '')
        # Count items mentioned
        pasta_names = ['Minestrone', 'Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna']
        mentioned = [p for p in pasta_names if p in answer]
        print(f"      Response: {answer[:80]}...")
        print(f"      Items mentioned: {len(mentioned)}")
    else:
        print(f"      Error: {response.status_code}")
    
    time.sleep(0.5)

# 5. Check menu data directly
print("\n5. CHECKING MENU DATA:")
response = requests.get("https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id=bella_vista_restaurant")
if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print(f"   Total menu items: {len(menu)}")
    
    # Check pasta items
    pasta_items = []
    stuffed_mushrooms_index = None
    
    for i, item in enumerate(menu):
        name = item.get('dish', '')
        if 'Stuffed Mushrooms' in name:
            stuffed_mushrooms_index = i
            
        if any(p in name.lower() for p in ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']):
            pasta_items.append((i, name))
    
    print(f"   Pasta items found: {len(pasta_items)}")
    for idx, name in pasta_items[:10]:
        print(f"      {idx}: {name}")
    
    if stuffed_mushrooms_index is not None:
        print(f"\n   Stuffed Mushrooms found at index: {stuffed_mushrooms_index}")
        item = menu[stuffed_mushrooms_index]
        print(f"      Description: {item.get('description', '')[:100]}")
        print(f"      Subcategory: {item.get('subcategory', '')}")

# 6. Test MIA backend directly
print("\n6. TESTING MIA BACKEND DIRECTLY:")
test_prompt = """You are a friendly restaurant assistant helping customers with menu questions.

ABSOLUTE REQUIREMENT: When asked about any food category (pasta, pizza, salad, etc.), you MUST list EVERY SINGLE item from that category shown in the context below. Do not select "examples" or "some options" - list them ALL.

Restaurant: bella_vista_restaurant
Customer asks: 'what pasta do you have'

Relevant menu information:
Main: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99), Penne Arrabbiata ($16.99), Seafood Linguine ($32.99), Gnocchi Gorgonzola ($19.99), Lasagna Bolognese ($20.99)

CRITICAL: You MUST list EVERY SINGLE item from the context above. Do not summarize, truncate, or give examples - list them ALL.

Customer: what pasta do you have
Assistant:"""

response = requests.post(
    "https://mia-backend-production.up.railway.app/api/generate",
    json={
        "prompt": test_prompt,
        "max_tokens": 250,
        "temperature": 0.7,
        "source": "restaurant"
    }
)

if response.status_code == 200:
    result = response.json()
    answer = result.get('text', result.get('response', ''))
    print(f"   MIA Response: {answer}")
    pasta_count = sum(1 for p in ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna'] if p in answer)
    print(f"   Pasta items mentioned: {pasta_count}/6")
else:
    print(f"   MIA Error: {response.status_code}")