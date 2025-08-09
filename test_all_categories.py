#!/usr/bin/env python3
"""
Test that all food categories return complete lists
"""
import requests
import json
import uuid
import time

print("Testing food category queries")
print("=" * 80)

# Test queries for different categories
test_queries = [
    "what pasta do you have",
    "what desserts do you have", 
    "show me your salads",
    "what seafood options do you have",
    "list your appetizers",
    "what wines do you have"
]

for query in test_queries:
    print(f"\nTesting: '{query}'")
    print("-" * 60)
    
    # Make request to restaurant backend
    client_id = str(uuid.uuid4())
    response = requests.post(
        'https://restaurantchat-production.up.railway.app/chat',
        json={
            'restaurant_id': 'bella_vista_restaurant',
            'client_id': client_id,
            'sender_type': 'client',
            'message': query
        },
        headers={'Content-Type': 'application/json'}
    )
    
    if response.status_code == 200:
        result = response.json()
        answer = result.get('answer', '')
        print(f"Response: {answer}")
        
        # Count items mentioned
        # Look for common patterns like commas, "and", numbers
        item_count = answer.count(',') + 1 if ',' in answer else 1
        print(f"Approximate items mentioned: {item_count}")
    else:
        print(f"Error: {response.status_code} - {response.text}")
    
    # Small delay between requests
    time.sleep(1)

# Also test with direct prompt to MIA
print("\n" + "=" * 80)
print("Testing direct MIA response for desserts:")

system_prompt = """
You are a friendly restaurant assistant helping customers with menu questions.

ABSOLUTE REQUIREMENT: When asked about any food category (pasta, pizza, salad, etc.), you MUST list EVERY SINGLE item from that category shown in the context below. Do not select "examples" or "some options" - list them ALL.

RULES:
1. "What pasta do you have" = List ALL pasta items, exactly as shown in context
2. "What are your pasta options" = List ALL pasta items, exactly as shown in context  
3. Never say "including" or "such as" - these imply there are more options not listed
4. Format: "We have [complete list of ALL items]" or "Our pasta dishes are [complete list]"
5. Treat these as equivalent: "what X do you have", "X options", "X choices", "X dishes"
6. Always respond in the same language as the customer's message

The context below contains the COMPLETE list. Your job is to relay it fully, not summarize.
"""

test_context = """
Restaurant: bella_vista_restaurant
Customer asks: 'what desserts do you have'

Relevant menu information:
Dessert: Tiramisu ($8.99), Chocolate Lava Cake ($9.99), Panna Cotta ($7.99), Gelato ($6.99), Cheesecake ($8.99)

CRITICAL: You MUST list EVERY SINGLE item from the context above. Do not summarize, truncate, or give examples - list them ALL.

Customer: what desserts do you have
Assistant:"""

response = requests.post(
    "https://mia-backend-production.up.railway.app/api/generate",
    json={
        "prompt": system_prompt + "\n" + test_context,
        "max_tokens": 250,
        "temperature": 0.7,
        "source": "test"
    }
)

if response.status_code == 200:
    result = response.json()
    answer = result.get('text', result.get('response', 'No response'))
    print(f"\nDirect MIA Response: {answer}")
else:
    print(f"Error: {response.status_code}")