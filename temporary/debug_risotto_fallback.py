#!/usr/bin/env python3
"""
Debug script to test the risotto fallback logic
"""

import requests
import json
import uuid

# Test the risotto search directly
API_URL = "https://restaurantchat-production.up.railway.app/chat"
RESTAURANT_ID = "bella_vista_restaurant"

def test_risotto_search():
    """Test risotto search and analyze the response"""
    print("🔍 Testing Risotto Search Fallback Logic")
    print("="*50)
    
    test_data = {
        'message': 'Show me risotto',
        'client_id': str(uuid.uuid4()),
        'restaurant_id': RESTAURANT_ID
    }
    
    try:
        response = requests.post(API_URL, json=test_data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            print(f"✅ Response received")
            print(f"📝 Answer: {answer}")
            
            # Extract debug info
            if '[DEBUG INFO]' in answer:
                debug_start = answer.find('[DEBUG INFO]')
                debug_text = answer[debug_start + 12:].strip()
                try:
                    debug_info = json.loads(debug_text)
                    print(f"\n🔧 Debug Info:")
                    print(json.dumps(debug_info, indent=2))
                    
                    # Check tool results
                    if 'tool_results_summary' in debug_info:
                        for tool_result in debug_info['tool_results_summary']:
                            if tool_result['tool'] == 'search_by_food_type':
                                print(f"\n📊 search_by_food_type results:")
                                print(f"   • Items found: {tool_result.get('items_found', 0)}")
                                print(f"   • Found: {tool_result.get('found', 0)}")
                                
                                # This should be 0 if fallback didn't work
                                if tool_result.get('found', 0) == 0:
                                    print("   ❌ FALLBACK NOT WORKING - Found 0 items")
                                else:
                                    print("   ✅ FALLBACK WORKING - Found items")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse debug info: {e}")
            else:
                print("❌ No debug info found in response")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_risotto_search()
