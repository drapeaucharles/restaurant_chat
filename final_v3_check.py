#!/usr/bin/env python3
"""Final check - what's happening with V3"""
import requests
import uuid

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

print("🔍 Final V3 Status Check\n")

# From the logs, I can see:
# INFO:routes.chat_dynamic:Restaurant bella_vista_restaurant using RAG mode: full_menu
# INFO:routes.chat_dynamic:Using full_menu_with_tools - AI will decide when to use tools

print("The server logs show:")
print("- bella_vista_restaurant is using RAG mode: full_menu")
print("- It's being upgraded to full_menu_with_tools")
print("- NOT using internal_tools_v3")
print("\nThis means:")
print("1. bella_vista_restaurant has rag_mode='full_menu' in the database")
print("2. The DEFAULT_RAG_MODE is not being used for this restaurant")
print("3. Need to update bella_vista_restaurant to rag_mode='internal_tools_v3' in DB")

# Let's test one more time to confirm
print("\n" + "="*60)
print("Confirming current behavior:")

response = requests.post(
    f"{BACKEND_URL}/chat",
    json={
        "restaurant_id": "bella_vista_restaurant",
        "client_id": str(uuid.uuid4()),
        "message": "I have a nut allergy",
        "sender_type": "customer"
    }
)

if response.status_code == 200:
    data = response.json()
    answer = data.get('answer', '')
    
    # Check for patterns
    if "[DEBUG:" in answer:
        print("❌ Has DEBUG output - using memory/diagnostic service")
    elif "I need to check our ingredient database" in answer:
        print("❌ Has safety validator message - using full_menu_with_tools")
    else:
        print("✅ Different pattern - might be V3")
        print(f"Response: {answer[:200]}...")
        
print("\n" + "="*60)
print("\nTo activate internal_tools_v3:")
print("UPDATE businesses SET rag_mode = 'internal_tools_v3' WHERE business_id = 'bella_vista_restaurant';")
print("\nThe DEFAULT_RAG_MODE only applies to restaurants without a specific rag_mode set.")