#!/usr/bin/env python3
"""Check restaurant RAG mode"""
import requests

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

# Get restaurant details
restaurant_id = "bella_vista_restaurant"

# Try to get diagnostic info
try:
    response = requests.get(f"{BACKEND_URL}/diagnostic")
    if response.status_code == 200:
        data = response.json()
        # Look for restaurant info in system diagnostics
        if "restaurants_info" in data:
            for r in data["restaurants_info"]:
                if r.get("restaurant_id") == restaurant_id:
                    print(f"Restaurant: {r.get('business_name', 'Unknown')}")
                    print(f"RAG Mode: {r.get('rag_mode', 'Not set')}")
except:
    pass

# Try memory check endpoint
try:
    response = requests.get(f"{BACKEND_URL}/memory-check/{restaurant_id}")
    if response.status_code == 200:
        data = response.json()
        print(f"\nMemory service info: {data}")
except:
    pass

# Check provider info
try:
    response = requests.get(f"{BACKEND_URL}/chat/provider")
    if response.status_code == 200:
        data = response.json()
        print(f"\nChat provider info:")
        print(f"  Available modes: {data.get('available_modes', [])}")
        print(f"  Default mode: {data.get('default_mode', 'unknown')}")
except:
    pass