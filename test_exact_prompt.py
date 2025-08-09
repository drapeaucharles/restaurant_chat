#!/usr/bin/env python3
"""
Test the exact prompt being sent to MIA
"""
import requests
import json

# Build the exact system prompt
system_prompt = """
You are a friendly restaurant assistant helping customers with menu questions.

CRITICAL RULES:
1. ONLY mention dishes that are explicitly listed in the context below
2. When asked about a category (like "pasta"), you MUST list ALL items shown in the context
3. NEVER truncate or shorten the list - if context shows 6 pasta dishes, mention all 6 by name
4. Format: "We have [list all items]" - be complete, not selective
5. Don't add extra commentary or descriptions unless specifically asked
6. Always respond in the same language as the customer's message

IMPORTANT: Customers want to know ALL their options. List every single item provided in the context.
"""

# Simulate the exact context that would be built
context = """
Restaurant: bella_vista_restaurant
Customer asks: 'What pasta do you have'

Relevant menu information:
Starter: Minestrone Soup ($8.99)
Main: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99), Penne Arrabbiata ($16.99), Seafood Linguine ($32.99), Gnocchi Gorgonzola ($19.99), Lasagna Bolognese ($20.99)

REMINDER: List ALL items from the context above - do not truncate or select just a few.

Customer: What pasta do you have
Assistant:"""

full_prompt = system_prompt + "\n" + context

print("Testing direct MIA response with full pasta context...")
print("=" * 60)

# Test with MIA backend
response = requests.post(
    "https://mia-backend-production.up.railway.app/api/generate",
    json={
        "prompt": full_prompt,
        "max_tokens": 250,
        "temperature": 0.7,
        "source": "test"
    }
)

if response.status_code == 200:
    result = response.json()
    answer = result.get('text', result.get('response', 'No response'))
    print(f"MIA Response: {answer}")
    
    # Count pasta mentions
    pasta_names = ['Minestrone', 'Spaghetti', 'Lobster Ravioli', 'Penne', 'Seafood Linguine', 'Gnocchi', 'Lasagna']
    mentioned = [p for p in pasta_names if p in answer]
    print(f"\nPasta dishes mentioned: {len(mentioned)}/{len(pasta_names)}")
    print(f"Which ones: {mentioned}")
else:
    print(f"Error: {response.status_code} - {response.text}")