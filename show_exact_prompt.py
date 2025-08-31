#!/usr/bin/env python3
"""Show the exact prompt structure sent to the miner"""

# Simulate what gets built
def show_exact_prompt():
    # From send_to_mia_with_tools function
    tools_instruction = """TOOLS (only use for food/menu questions):

IF customer asks about food/menu (like "I want fish", "what vegetarian options"), respond with ONLY:
<tool_call>
{"name": "search_menu_items", "parameters": {"search_term": "fish", "search_type": "ingredient"}}
</tool_call>

IF customer says hello, thanks, or non-food things, just respond normally without tools.

Available tools:
"""
    
    tools_description = """- search_menu_items: Search for menu items by ingredient, category, or name
- get_dish_details: Get complete details about a specific dish
- filter_by_dietary: Find dishes suitable for dietary restrictions
"""

    personality = "\nYou are Maria, a friendly server at Bella Vista Restaurant.\n\n"
    
    # Simulated conversation history
    conversation_history = """Recent conversation:
Customer: Hello
Maria: Hello! Welcome to Bella Vista Restaurant. How can I help you today?
Customer: I want meat
Maria: Here are our meat dishes: Ribeye Steak $38.99, Grilled Chicken $24.99...
"""

    # Current message
    current_prompt = """Customer: Sorry I change my mind, I would like fish
Assistant:"""

    # EXACT STRUCTURE SENT TO MINER:
    full_prompt = tools_instruction + tools_description + personality + conversation_history + current_prompt
    
    print("=== EXACT PROMPT SENT TO MINER ===\n")
    print(full_prompt)
    print("\n=== END OF PROMPT ===")
    
    # What miner receives as JSON
    print("\n\n=== WHAT MINER RECEIVES (via get_mia_response_hybrid) ===\n")
    import json
    request_to_miner = {
        "message": full_prompt,
        "max_tokens": 300,
        "temperature": 0.7
    }
    print(json.dumps(request_to_miner, indent=2))

if __name__ == "__main__":
    show_exact_prompt()