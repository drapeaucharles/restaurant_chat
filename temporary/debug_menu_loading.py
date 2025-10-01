#!/usr/bin/env python3
"""
Debug script to test menu loading
"""

import requests
import uuid
import json

def test_menu_loading():
    """Test different queries to see what menu data is being loaded"""
    
    test_cases = [
        "Show me all menu items",
        "Show me the full menu", 
        "What's on your menu?",
        "Show me vegetarian options",
        "Show me pasta dishes"
    ]
    
    for query in test_cases:
        print(f"\n🧪 Testing: {query}")
        
        test_data = {
            'message': query,
            'client_id': str(uuid.uuid4()),
            'restaurant_id': 'bella_vista_restaurant'
        }
        
        response = requests.post('https://restaurantchat-production.up.railway.app/chat', json=test_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            # Count items mentioned
            lines = answer.split('\n')
            item_count = 0
            for line in lines:
                if line.strip().startswith('-') and '$' in line:
                    item_count += 1
            
            print(f"Items mentioned: {item_count}")
            print(f"Response length: {len(answer)} chars")
            
            # Show first 200 chars
            print(f"Response: {answer[:200]}...")
        else:
            print(f"Error: {response.status_code}")

if __name__ == "__main__":
    test_menu_loading()

