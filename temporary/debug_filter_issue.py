#!/usr/bin/env python3
"""
Debug script to test the filter_dietary_food_type issue
"""

import requests
import uuid
import json

def test_query(message, expected_tool=None):
    """Test a specific query and show debug info"""
    print(f"\n🧪 Testing: {message}")
    
    test_data = {
        'message': message,
        'client_id': str(uuid.uuid4()),
        'restaurant_id': 'bella_vista_restaurant'
    }
    
    response = requests.post('https://restaurantchat-production.up.railway.app/chat', json=test_data, timeout=30)
    if response.status_code == 200:
        result = response.json()
        answer = result.get('answer', '')
        
        # Parse debug info
        if '[DEBUG INFO]' in answer:
            debug_start = answer.find('[DEBUG INFO]') + len('[DEBUG INFO]')
            debug_end = answer.find('}', debug_start) + 1
            debug_json = answer[debug_start:debug_end].strip()
            try:
                debug_info = json.loads(debug_json)
                tools = debug_info.get('phase1_tools_selected', [])
                print(f"✅ Tool used: {tools[0].get('tool') if tools else 'None'}")
                print(f"✅ Parameters: {tools[0].get('parameters') if tools else 'None'}")
            except:
                print("❌ Could not parse debug info")
        
        print(f"Response: {answer[:200]}...")
        
        # Check if it found items
        if 'do not have' in answer.lower():
            print("❌ No items found")
        else:
            print("✅ Found items!")
            
    else:
        print(f"❌ HTTP Error: {response.status_code}")

def main():
    print("🔍 Debugging filter_dietary_food_type issue...")
    
    # Test cases
    test_query("Show me vegetarian options", "filter_dietary")
    test_query("Show me pasta dishes", "search_by_food_type") 
    test_query("Show me vegetarian pasta", "filter_dietary_food_type")
    test_query("Show me vegan pasta", "filter_dietary_food_type")
    test_query("Show me vegan options", "filter_dietary")

if __name__ == "__main__":
    main()

