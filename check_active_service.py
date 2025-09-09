#!/usr/bin/env python3
"""Check which service is actually being used"""
import requests

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

# Check chat provider info
try:
    response = requests.get(f"{BACKEND_URL}/chat/provider")
    if response.status_code == 200:
        data = response.json()
        print("Chat Provider Information:")
        print(f"  Provider: {data.get('provider')}")
        print(f"  Available modes: {data.get('available_modes', [])}")
        print(f"  Default mode: {data.get('default_mode')}")
        print(f"  Features: {data.get('features', [])}")
        
        # Check if internal_tools_v3 is in available modes
        if 'internal_tools_v3' in data.get('available_modes', []):
            print("\n✅ internal_tools_v3 is available!")
        else:
            print("\n❌ internal_tools_v3 is NOT in available modes!")
            
except Exception as e:
    print(f"Error: {e}")

# Check version
try:
    response = requests.get(f"{BACKEND_URL}/version")
    if response.status_code == 200:
        data = response.json()
        print(f"\nVersion info: {data}")
except:
    pass