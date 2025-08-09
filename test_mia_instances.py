#!/usr/bin/env python3
"""
Test both MIA instances to see the difference
"""
import requests

# Test prompt with all pasta listed
test_prompt = """You are a friendly restaurant assistant helping customers with menu questions.

ABSOLUTE REQUIREMENT: When asked about any food category (pasta, pizza, salad, etc.), you MUST list EVERY SINGLE item from that category shown in the context below. Do not select "examples" or "some options" - list them ALL.

Restaurant: bella_vista_restaurant
Customer asks: 'what pasta do you have'

Relevant menu information:
Main: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99), Penne Arrabbiata ($16.99), Seafood Linguine ($32.99), Gnocchi Gorgonzola ($19.99), Lasagna Bolognese ($20.99)

CRITICAL: You MUST list EVERY SINGLE item from the context above. Do not summarize, truncate, or give examples - list them ALL.

Customer: what pasta do you have
Assistant:"""

print("Testing MIA Instances")
print("=" * 80)

# 1. Test remote MIA backend
print("\n1. REMOTE MIA BACKEND (https://mia-backend-production.up.railway.app):")
try:
    response = requests.post(
        "https://mia-backend-production.up.railway.app/api/generate",
        json={
            "prompt": test_prompt,
            "max_tokens": 250,
            "temperature": 0.7,
            "source": "test"
        },
        timeout=10
    )
    
    if response.status_code == 200:
        answer = response.json().get('text', response.json().get('response', ''))
        print(f"   Response: {answer}")
        pasta_count = sum(1 for p in ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna'] if p in answer)
        print(f"   Pasta items mentioned: {pasta_count}/6")
    else:
        print(f"   Error: {response.status_code}")
except Exception as e:
    print(f"   Exception: {e}")

# 2. Test what local MIA would return (we can't access it directly from outside)
print("\n2. LOCAL MIA (via Restaurant Backend):")
print("   The restaurant backend is using a local MIA instance at http://localhost:8000")
print("   This is why responses are different - the local instance is not following instructions")

# 3. Test with different prompts
print("\n3. TESTING DIFFERENT PROMPTS ON REMOTE MIA:")
variations = [
    "what pasta do you have",
    "list all pasta",
    "show me your pasta"
]

for query in variations:
    prompt = test_prompt.replace("what pasta do you have", query)
    response = requests.post(
        "https://mia-backend-production.up.railway.app/api/generate",
        json={
            "prompt": prompt,
            "max_tokens": 250,
            "temperature": 0.7,
            "source": "test"
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('text', response.json().get('response', ''))
        pasta_count = sum(1 for p in ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna'] if p in answer)
        print(f"\n   Query: '{query}'")
        print(f"   Response: {answer[:80]}...")
        print(f"   Items: {pasta_count}/6")

# 4. Check if we can force remote MIA
print("\n4. SOLUTION OPTIONS:")
print("   a) Disable local MIA fallback in mia_chat_service.py")
print("   b) Set CHAT_PROVIDER=mia environment variable (not mia_local)")
print("   c) Fix the local MIA miner to follow instructions better")
print("   d) Remove the local MIA URL so it always uses remote")