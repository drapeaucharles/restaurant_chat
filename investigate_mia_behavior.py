#!/usr/bin/env python3
"""
Investigate MIA model behavior with different prompts and contexts
"""
import requests
import json

print("MIA Model Behavior Investigation")
print("=" * 80)

# Base context with all pasta items
pasta_context = """Main: Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99), Penne Arrabbiata ($16.99), Seafood Linguine ($32.99), Gnocchi Gorgonzola ($19.99), Lasagna Bolognese ($20.99)"""

# Test different prompt strategies
test_cases = [
    {
        "name": "Original prompt",
        "prompt": f"""You are a friendly restaurant assistant helping customers with menu questions.

ABSOLUTE REQUIREMENT: When asked about any food category (pasta, pizza, salad, etc.), you MUST list EVERY SINGLE item from that category shown in the context below. Do not select "examples" or "some options" - list them ALL.

Restaurant: bella_vista_restaurant
Customer asks: 'what pasta do you have'

Relevant menu information:
{pasta_context}

CRITICAL: You MUST list EVERY SINGLE item from the context above. Do not summarize, truncate, or give examples - list them ALL.

Customer: what pasta do you have
Assistant:"""
    },
    {
        "name": "Numbered list instruction",
        "prompt": f"""You are a restaurant assistant. 

INSTRUCTION: List ALL pasta dishes shown below as a numbered list. Do not skip any.

Available pasta:
{pasta_context}

Customer: what pasta do you have
Assistant: Here are ALL our pasta dishes:
1."""
    },
    {
        "name": "Count requirement",
        "prompt": f"""You are a restaurant assistant.

Context shows EXACTLY 6 pasta dishes. You MUST list all 6.

{pasta_context}

Customer: what pasta do you have
Assistant: We have all 6 pasta dishes:"""
    },
    {
        "name": "Completion style",
        "prompt": f"""Complete this response by listing ALL items:

Menu: {pasta_context}

Customer: what pasta do you have
Assistant: We have Spaghetti Carbonara ($18.99), Lobster Ravioli ($28.99),"""
    },
    {
        "name": "JSON instruction",
        "prompt": f"""List all pasta dishes from the context in this exact format:

Context: {pasta_context}

Customer: what pasta do you have
Assistant: We have the following pasta dishes: [Spaghetti Carbonara, Lobster Ravioli,"""
    },
    {
        "name": "Explicit enumeration",
        "prompt": f"""Context contains these pasta dishes:
1. Spaghetti Carbonara ($18.99)
2. Lobster Ravioli ($28.99)
3. Penne Arrabbiata ($16.99)
4. Seafood Linguine ($32.99)
5. Gnocchi Gorgonzola ($19.99)
6. Lasagna Bolognese ($20.99)

Customer: what pasta do you have
Assistant: We have"""
    }
]

# Test each prompt
for i, test in enumerate(test_cases):
    print(f"\n{i+1}. {test['name']}:")
    print("-" * 60)
    
    response = requests.post(
        "https://mia-backend-production.up.railway.app/api/generate",
        json={
            "prompt": test['prompt'],
            "max_tokens": 200,
            "temperature": 0.3,  # Lower temperature for more consistent output
            "source": "test"
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('text', response.json().get('response', ''))
        print(f"Response: {answer}")
        
        # Count pasta mentions
        pasta_names = ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna']
        mentioned = sum(1 for p in pasta_names if p in answer)
        print(f"Items mentioned: {mentioned}/6")
    else:
        print(f"Error: {response.status_code}")

# Test with different temperatures
print("\n\nTESTING TEMPERATURE EFFECT:")
print("=" * 80)
for temp in [0.1, 0.5, 0.7, 1.0]:
    print(f"\nTemperature {temp}:")
    response = requests.post(
        "https://mia-backend-production.up.railway.app/api/generate",
        json={
            "prompt": test_cases[0]['prompt'],  # Use original prompt
            "max_tokens": 200,
            "temperature": temp,
            "source": "test"
        }
    )
    
    if response.status_code == 200:
        answer = response.json().get('text', response.json().get('response', ''))
        mentioned = sum(1 for p in ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna'] if p in answer)
        print(f"  Items mentioned: {mentioned}/6 - {answer[:60]}...")

# Test context position
print("\n\nTESTING CONTEXT POSITION:")
print("=" * 80)

# Context at end
prompt_end = f"""Customer: what pasta do you have

You are a restaurant assistant. List ALL items below:

{pasta_context}