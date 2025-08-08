#!/usr/bin/env python3
"""
Diagnostic script to analyze context and menu passing to MIA
"""
import requests
import json
from datetime import datetime

print("Restaurant Context Analysis Report")
print("=" * 60)
print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Configuration
RESTAURANT_URL = "https://restaurantchat-production.up.railway.app"
MIA_URL = "https://mia-backend-production.up.railway.app"
restaurant_id = "bella_vista_restaurant"

# 1. Check Restaurant Data
print("1. RESTAURANT DATA ANALYSIS")
print("-" * 40)
try:
    response = requests.get(f"{RESTAURANT_URL}/restaurant/info?restaurant_id={restaurant_id}")
    if response.status_code == 200:
        restaurant_info = response.json()
        print(f"Restaurant Name: {restaurant_info.get('name', 'Unknown')}")
        
        # Check menu data
        data = restaurant_info.get('data', {})
        menu = data.get('menu', [])
        print(f"Menu Items Count: {len(menu)}")
        
        if menu:
            print("\nFirst 5 Menu Items:")
            for i, item in enumerate(menu[:5], 1):
                name = item.get('name') or item.get('dish', 'No name')
                ingredients = item.get('ingredients', [])
                print(f"  {i}. {name}")
                print(f"     Ingredients: {', '.join(ingredients[:3])}...")
        else:
            print("  WARNING: No menu items found!")
            
        # Check other data
        print(f"\nOpening Hours: {data.get('opening_hours', 'Not set')}")
        print(f"Contact Info: {data.get('contact_info', 'Not set')}")
    else:
        print(f"ERROR: Failed to get restaurant info: {response.status_code}")
except Exception as e:
    print(f"ERROR: {e}")

print("\n2. CONTEXT BUILDING ANALYSIS")
print("-" * 40)

# Test different types of queries to see what context is built
test_queries = [
    {
        "query": "What vegetarian dishes do you have?",
        "expected_context": "Should include vegetarian menu items"
    },
    {
        "query": "Tell me about your pasta dishes",
        "expected_context": "Should include pasta-related items"
    },
    {
        "query": "What are your hours?",
        "expected_context": "Should include opening hours"
    },
    {
        "query": "Do you have any specials today?",
        "expected_context": "Should include popular/recommended items"
    }
]

print("\n3. MIA PROMPT ANALYSIS")
print("-" * 40)

# Simulate what the restaurant service would send
for test in test_queries[:2]:  # Test first 2 queries
    print(f"\nQuery: '{test['query']}'")
    print(f"Expected: {test['expected_context']}")
    
    # Build a sample prompt like the restaurant service would
    system_prompt = """You are a friendly restaurant assistant. The customer is viewing our complete menu on their screen.

CRITICAL RULES:
1. If an item is NOT in the provided context, it's NOT on our menu - say "We don't have [item], but..."
2. When something isn't available, suggest a similar item from the context if possible
3. ONLY mention items explicitly provided in the context - these are our actual menu items
4. They can see the menu, so don't list everything
5. Be concise and helpful - max 2-3 sentences
6. For ingredients/allergens: only answer if you have the specific info, otherwise say you'll check
7. Always respond in the same language as the customer's message"""

    # Simulate menu context (simplified)
    menu_context = ""
    if "vegetarian" in test['query'].lower():
        menu_context = "Relevant menu items: [EXACT: Margherita Pizza]: tomato sauce, mozzarella, basil; [EXACT: Caprese Salad]: tomatoes, mozzarella, basil"
    elif "pasta" in test['query'].lower():
        menu_context = "Relevant menu items: [EXACT: Spaghetti Carbonara]: pasta, eggs, bacon, parmesan; [EXACT: Penne Arrabbiata]: pasta, tomato sauce, chili"
    
    full_prompt = f"""{system_prompt}

Restaurant: {restaurant_id}
Customer asks: '{test['query']}'
(Customer is viewing the complete menu on their screen)
{menu_context}

Customer: {test['query']}
Assistant:"""

    print("\nGenerated Prompt Preview (first 500 chars):")
    print(full_prompt[:500] + "...")
    
    # Test with MIA
    try:
        response = requests.post(
            f"{MIA_URL}/api/generate",
            json={
                "prompt": full_prompt,
                "source": "diagnostic",
                "max_tokens": 100
            }
        )
        if response.status_code == 200:
            result = response.json()
            print(f"\nMIA Response: {result.get('text', 'No text')[:200]}...")
            print(f"Source: {result.get('source')}")
        else:
            print(f"ERROR: MIA returned {response.status_code}")
    except Exception as e:
        print(f"ERROR calling MIA: {e}")

print("\n4. RECOMMENDATIONS")
print("-" * 40)
print("Based on this analysis:")
print("1. Check if restaurant.data contains the full menu")
print("2. Verify format_menu_for_context is not filtering out too much")
print("3. Consider sending more complete menu context for general queries")
print("4. Ensure the prompt includes enough menu information")

print("\n" + "=" * 60)
print("Analysis Complete")