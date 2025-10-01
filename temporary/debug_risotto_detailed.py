#!/usr/bin/env python3
"""
Detailed debug script to test risotto search step by step
"""

import requests
import json
import uuid

# Test the risotto search directly
API_URL = "https://restaurantchat-production.up.railway.app/chat"
RESTAURANT_ID = "bella_vista_restaurant"

def test_risotto_search_detailed():
    """Test risotto search with detailed analysis"""
    print("🔍 Detailed Risotto Search Debug")
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
                    
                    # Check if we can find any logs about the fallback
                    if 'No category matches found' in answer:
                        print("✅ FALLBACK LOG FOUND - The fallback was triggered")
                    else:
                        print("❌ NO FALLBACK LOG - The fallback was NOT triggered")
                    
                    if 'Partial name matching found' in answer:
                        print("✅ PARTIAL MATCHING LOG FOUND - The fallback found items")
                    else:
                        print("❌ NO PARTIAL MATCHING LOG - The fallback found no items")
                    
                except json.JSONDecodeError as e:
                    print(f"❌ Failed to parse debug info: {e}")
            else:
                print("❌ No debug info found in response")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Exception: {e}")

def test_other_food_types():
    """Test other food types to see if fallback works for them"""
    print("\n🔍 Testing Other Food Types for Fallback")
    print("="*50)
    
    test_cases = [
        "Show me arancini",
        "Show me gnocchi", 
        "Show me carbonara"
    ]
    
    for message in test_cases:
        print(f"\n📝 Testing: {message}")
        test_data = {
            'message': message,
            'client_id': str(uuid.uuid4()),
            'restaurant_id': RESTAURANT_ID
        }
        
        try:
            response = requests.post(API_URL, json=test_data, timeout=30)
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                
                if 'do not have' in answer.lower():
                    print(f"   ❌ Not found: {answer[:100]}...")
                else:
                    print(f"   ✅ Found: {answer[:100]}...")
                    
                # Check for fallback logs
                if 'No category matches found' in answer:
                    print(f"   ✅ FALLBACK TRIGGERED")
                else:
                    print(f"   ❌ NO FALLBACK")
                    
            else:
                print(f"   ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_risotto_search_detailed()
    test_other_food_types()

