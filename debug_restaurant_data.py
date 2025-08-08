#!/usr/bin/env python3
"""
Debug script to check restaurant data structure
"""
import requests
import json

RESTAURANT_URL = "https://restaurantchat-production.up.railway.app"
restaurant_id = "bella_vista_restaurant"

print("Debugging Restaurant Data Structure")
print("=" * 50)

# Get full restaurant info
try:
    response = requests.get(f"{RESTAURANT_URL}/restaurant/info?restaurant_id={restaurant_id}")
    if response.status_code == 200:
        data = response.json()
        
        # Pretty print the entire structure
        print("Full Restaurant Data:")
        print(json.dumps(data, indent=2))
        
        print("\n" + "=" * 50)
        print("Data Analysis:")
        print(f"- Has 'data' field: {'data' in data}")
        if 'data' in data:
            print(f"- Type of 'data': {type(data['data'])}")
            print(f"- Keys in 'data': {list(data['data'].keys()) if isinstance(data['data'], dict) else 'Not a dict'}")
            
            if isinstance(data['data'], dict) and 'menu' in data['data']:
                menu = data['data']['menu']
                print(f"- Menu type: {type(menu)}")
                print(f"- Menu length: {len(menu) if isinstance(menu, list) else 'Not a list'}")
                if isinstance(menu, list) and len(menu) > 0:
                    print(f"- First menu item keys: {list(menu[0].keys())}")
        
        # Check for menu in other places
        print("\nSearching for menu in other locations:")
        for key in data.keys():
            if 'menu' in key.lower():
                print(f"- Found key '{key}' with type {type(data[key])}")
            if isinstance(data.get(key), dict):
                for subkey in data[key].keys():
                    if 'menu' in subkey.lower():
                        print(f"- Found nested key '{key}.{subkey}'")
                        
    else:
        print(f"ERROR: HTTP {response.status_code}")
        print(response.text)
        
except Exception as e:
    print(f"ERROR: {e}")