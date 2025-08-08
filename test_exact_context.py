#!/usr/bin/env python3
"""
Test exact context building for pasta query
"""
import requests
import json

print("Testing exact prompt sent to MIA for 'what pasta do you have'")
print("=" * 60)

# Build the exact prompt that would be sent
system_prompt = """
You are a friendly restaurant assistant helping customers with menu questions.

CRITICAL RULES:
1. ONLY mention dishes that are explicitly listed in the context below
2. Be direct and helpful - don't mention what you don't have unless specifically asked
3. For specific queries (like "pasta"), just list the relevant items we DO have
4. Keep responses concise (2-3 sentences max)
5. Don't categorize by course unless the context shows it that way
6. Always respond in the same language as the customer's message
"""

# Get the context that would be built
response = requests.post(
    "https://mia-backend-production.up.railway.app/api/generate",
    json={
        "prompt": system_prompt + "\n\nRestaurant: bella_vista_restaurant\nCustomer asks: 'what pasta do you have'\n\nRelevant menu information:\nMain: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99), Penne Arrabbiata ($16.99), Seafood Linguine ($32.99), Gnocchi Gorgonzola ($19.99), Lasagna Bolognese ($20.99)\n\nCustomer: what pasta do you have\nAssistant:",
        "source": "test",
        "max_tokens": 100
    }
)

if response.status_code == 200:
    result = response.json()
    print("Response with all pasta items in context:")
    print(result.get('text'))
    print("\n" + "-" * 60)
    
# Now test with limited context (what might be happening)
response2 = requests.post(
    "https://mia-backend-production.up.railway.app/api/generate",
    json={
        "prompt": system_prompt + "\n\nRestaurant: bella_vista_restaurant\nCustomer asks: 'what pasta do you have'\n\nRelevant menu information:\nMain: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99)\n\nCustomer: what pasta do you have\nAssistant:",
        "source": "test",
        "max_tokens": 100
    }
)

if response2.status_code == 200:
    result2 = response2.json()
    print("\nResponse with limited pasta items in context:")
    print(result2.get('text'))