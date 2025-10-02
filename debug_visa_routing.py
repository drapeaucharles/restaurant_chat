#!/usr/bin/env python3
"""
Debug script to test visa routing and service
"""
import requests
import json

def test_visa_routing():
    """Test if GSI is properly routed to visa service"""
    
    # Test 1: Simple visa question
    print("🧪 Testing GSI Bali Agency routing...")
    
    test_data = {
        'message': 'I need visa help',
        'client_id': '123e4567-e89b-12d3-a456-426614174000',
        'restaurant_id': 'gsi_bali_agency'
    }
    
    try:
        response = requests.post(
            "https://restaurantchat-production.up.railway.app/chat",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            print(f"✅ Response received:")
            print(f"📝 Answer: {answer[:200]}...")
            
            # Check debug info
            if '[DEBUG INFO]' in answer:
                debug_start = answer.find('[DEBUG INFO]')
                debug_text = answer[debug_start + 12:].strip()
                try:
                    debug_info = json.loads(debug_text)
                    print(f"\n🔍 Debug Info:")
                    print(f"   Flow: {debug_info.get('flow', 'unknown')}")
                    
                    if 'phase1_tools_selected' in debug_info:
                        tools = [tool['tool'] for tool in debug_info['phase1_tools_selected']]
                        print(f"   Tools used: {tools}")
                        
                        # Check if using restaurant tools (bad) or visa tools (good)
                        restaurant_tools = ['search_menu_general', 'search_by_food_type', 'ask_clarify', 'restaurant_info']
                        visa_tools = ['visa.v1.profile.upsert_partial', 'visa.v1.catalog.get_products']
                        
                        using_restaurant_tools = any(tool in restaurant_tools for tool in tools)
                        using_visa_tools = any(tool.startswith('visa.v1.') for tool in tools)
                        
                        if using_restaurant_tools:
                            print(f"   ❌ PROBLEM: Using restaurant tools for visa agency!")
                        elif using_visa_tools:
                            print(f"   ✅ GOOD: Using visa tools")
                        else:
                            print(f"   ⚠️ UNKNOWN: Using other tools")
                    
                except json.JSONDecodeError:
                    print(f"   ⚠️ Could not parse debug info")
            
            # Analyze response content
            if 'ingredient' in answer.lower() or 'allergen' in answer.lower():
                print(f"   ❌ PROBLEM: Response mentions food ingredients/allergens!")
            elif 'visa' in answer.lower() or 'permit' in answer.lower():
                print(f"   ✅ GOOD: Response is visa-related")
            else:
                print(f"   ⚠️ UNCLEAR: Response content unclear")
                
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            print(f"   Response: {response.text}")
            
    except Exception as e:
        print(f"❌ Request failed: {e}")

def test_restaurant_routing():
    """Test that regular restaurants still work"""
    print(f"\n🧪 Testing regular restaurant routing...")
    
    test_data = {
        'message': 'Show me pasta',
        'client_id': '123e4567-e89b-12d3-a456-426614174001', 
        'restaurant_id': 'bella_vista_restaurant'
    }
    
    try:
        response = requests.post(
            "https://restaurantchat-production.up.railway.app/chat",
            json=test_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            print(f"✅ Restaurant response received:")
            print(f"📝 Answer: {answer[:100]}...")
            
            if 'pasta' in answer.lower() or 'menu' in answer.lower():
                print(f"   ✅ GOOD: Restaurant response about food")
            else:
                print(f"   ⚠️ Unexpected restaurant response")
                
        else:
            print(f"❌ Restaurant HTTP Error: {response.status_code}")
            
    except Exception as e:
        print(f"❌ Restaurant request failed: {e}")

if __name__ == "__main__":
    print("🚀 Debugging Visa Routing vs Restaurant Routing")
    print("=" * 60)
    
    test_visa_routing()
    test_restaurant_routing()
    
    print(f"\n" + "=" * 60)
    print("🎯 Summary:")
    print("- GSI should use visa flows (visa.v1.* tools)")
    print("- Restaurants should use restaurant tools (search_menu_*, etc.)")
    print("- No ingredients/allergens for visa agencies!")
