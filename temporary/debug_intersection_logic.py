#!/usr/bin/env python3
"""
Debug script to test the intersection logic step by step
"""

import requests
import uuid
import json

def test_step_by_step():
    """Test each step of the filtering process"""
    
    print("🔍 Testing step-by-step filtering logic...")
    
    # Step 1: Test vegetarian filter only
    print("\n1️⃣ Testing vegetarian filter only:")
    test_data = {
        'message': 'Show me vegetarian options',
        'client_id': str(uuid.uuid4()),
        'restaurant_id': 'bella_vista_restaurant'
    }
    
    response = requests.post('https://restaurantchat-production.up.railway.app/chat', json=test_data, timeout=30)
    if response.status_code == 200:
        result = response.json()
        answer = result.get('answer', '')
        print(f"✅ Found vegetarian items: {answer[:100]}...")
    else:
        print(f"❌ Error: {response.status_code}")
    
    # Step 2: Test pasta filter only
    print("\n2️⃣ Testing pasta filter only:")
    test_data = {
        'message': 'Show me pasta dishes',
        'client_id': str(uuid.uuid4()),
        'restaurant_id': 'bella_vista_restaurant'
    }
    
    response = requests.post('https://restaurantchat-production.up.railway.app/chat', json=test_data, timeout=30)
    if response.status_code == 200:
        result = response.json()
        answer = result.get('answer', '')
        print(f"✅ Found pasta items: {answer[:100]}...")
    else:
        print(f"❌ Error: {response.status_code}")
    
    # Step 3: Test combined filter
    print("\n3️⃣ Testing combined vegetarian + pasta filter:")
    test_data = {
        'message': 'Show me vegetarian pasta',
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
                tool_results = debug_info.get('tool_results_summary', [])
                
                print(f"✅ Tool used: {tools[0].get('tool') if tools else 'None'}")
                print(f"✅ Parameters: {tools[0].get('parameters') if tools else 'None'}")
                print(f"✅ Items found: {tool_results[0].get('found') if tool_results else 'None'}")
            except Exception as e:
                print(f"❌ Debug parse error: {e}")
        
        print(f"Response: {answer[:200]}...")
    else:
        print(f"❌ Error: {response.status_code}")

if __name__ == "__main__":
    test_step_by_step()

