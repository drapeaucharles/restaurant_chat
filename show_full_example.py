#!/usr/bin/env python3
"""Show complete example of tool calling flow"""

def show_full_flow():
    print("=== COMPLETE TOOL CALLING FLOW EXAMPLE ===\n")
    
    print("STEP 1: Customer says 'I want fish'\n")
    print("-" * 60)
    
    print("\nSTEP 2: Backend builds this prompt for MIA:\n")
    prompt_to_mia = """TOOLS (only use for food/menu questions):

IF customer asks about food/menu (like "I want fish", "what vegetarian options"), respond with ONLY:
<tool_call>
{"name": "search_menu_items", "parameters": {"search_term": "fish", "search_type": "ingredient"}}
</tool_call>

IF customer says hello, thanks, or non-food things, just respond normally without tools.

Available tools:
- search_menu_items: Search for menu items by ingredient, category, or name
- get_dish_details: Get complete details about a specific dish
- filter_by_dietary: Find dishes suitable for dietary restrictions

You are Maria, a friendly server at Bella Vista Restaurant.

Customer: I want fish
Assistant:"""
    
    print(prompt_to_mia)
    print("\n" + "-" * 60)
    
    print("\nSTEP 3: MIA SHOULD respond with ONLY this:\n")
    expected_response = """<tool_call>
{"name": "search_menu_items", "parameters": {"search_term": "fish", "search_type": "ingredient"}}
</tool_call>"""
    print(expected_response)
    
    print("\n" + "-" * 60)
    print("\nSTEP 4: Backend detects tool call and executes search:\n")
    print("Searching database for 'fish'...")
    print("Found 5 items:")
    search_results = """- Grilled Salmon - $26.99
- Seafood Linguine - $32.99  
- Sea Bass - $32.99
- Tuna Steak - $34.99
- Mixed Seafood Grill - $42.99"""
    print(search_results)
    
    print("\n" + "-" * 60)
    print("\nSTEP 5: Backend sends results back to MIA:\n")
    
    second_prompt = """You are Maria at Bella Vista Restaurant.

Previous conversation:
Customer: I want fish
You used a tool and got this result:

Here are 5 options:
- Grilled Salmon - $26.99
- Seafood Linguine - $32.99
- Sea Bass - $32.99
- Tuna Steak - $34.99
- Mixed Seafood Grill - $42.99

Now provide a natural, friendly response to the customer using this information:"""
    
    print(second_prompt)
    
    print("\n" + "-" * 60)
    print("\nSTEP 6: MIA gives final response to customer:\n")
    
    final_response = """Excellent choice! We have some wonderful fish options for you today:

Our Grilled Salmon at $26.99 is perfectly seasoned and cooked to perfection. The Seafood Linguine ($32.99) is a customer favorite with a mix of fresh seafood in a light garlic sauce. 

For something special, I'd recommend our Mixed Seafood Grill at $42.99 - it has a variety of fresh catches of the day.

What sounds good to you?"""
    
    print(final_response)
    
    print("\n" + "=" * 60)
    print("\nWHAT'S CURRENTLY HAPPENING (PROBLEM):\n")
    print("Instead of the proper <tool_call> format, MIA responds with:")
    print("- 'search_menu_items' (just the name)")
    print("- 'Let me search for fish options' (natural language)")
    print("- Or tries to answer without using tools at all")
    
    print("\n" + "=" * 60)
    print("\nJSON STRUCTURE SENT TO MINER:\n")
    import json
    miner_request = {
        "message": prompt_to_mia,
        "max_tokens": 300,
        "temperature": 0.7
    }
    print(json.dumps(miner_request, indent=2)[:500] + "...")

if __name__ == "__main__":
    show_full_flow()