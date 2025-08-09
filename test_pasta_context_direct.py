#!/usr/bin/env python3
"""
Test pasta context building directly
"""
import sys
sys.path.append('/home/charles-drapeau/Documents/Project/Restaurant/BackEnd')

from services.mia_chat_service import format_menu_for_context
import requests
import json

# Get restaurant data
restaurant_id = "bella_vista_restaurant"
response = requests.get(f"https://restaurantchat-production.up.railway.app/restaurant/info?restaurant_id={restaurant_id}")

if response.status_code == 200:
    data = response.json()
    menu = data.get('menu', [])
    
    print(f"Total menu items: {len(menu)}")
    
    # Test the context building directly
    pasta_context = format_menu_for_context(menu, "what pasta do you have")
    
    print("\nContext generated for 'what pasta do you have':")
    print("=" * 60)
    print(pasta_context)
    print("=" * 60)
    
    # Count pasta mentions in context
    pasta_keywords = ['Spaghetti', 'Linguine', 'Penne', 'Ravioli', 'Lasagna', 'Gnocchi', 'Minestrone']
    mentioned = [k for k in pasta_keywords if k in pasta_context]
    print(f"\nPasta dishes mentioned in context: {len(mentioned)}")
    print(f"Which ones: {mentioned}")
else:
    print(f"Error: {response.status_code}")