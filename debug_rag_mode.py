#!/usr/bin/env python3
"""Debug which RAG mode is being selected"""
import requests
import json

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

# Get all businesses to see their settings
print("🔍 Checking businesses and their RAG modes\n")

response = requests.get(f"{BACKEND_URL}/businesses")
if response.status_code == 200:
    businesses = response.json().get('businesses', [])
    for b in businesses:
        if b['business_id'] == 'bella_vista_restaurant':
            print(f"Found Bella Vista:")
            print(f"  ID: {b['business_id']}")
            print(f"  Name: {b['name']}")
            print(f"  Type: {b['type']}")
            print(f"  Has rag_mode field? {json.dumps(b, indent=2)}")
            break
    else:
        print("bella_vista_restaurant not found in businesses list")
        
print("\n" + "="*60)
print("The issue appears to be:")
print("1. bella_vista_restaurant's rag_mode might not be visible via the API")
print("2. The system might be using DEFAULT_RAG_MODE=memory_universal")
print("3. Need to verify the database update was successful")
print("\nTo fix:")
print("- Either update DEFAULT_RAG_MODE in .env to internal_tools_v3")
print("- Or ensure bella_vista_restaurant has rag_mode='internal_tools_v3' in DB")