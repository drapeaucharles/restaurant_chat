#!/usr/bin/env python3
"""Verify V3 is deployed and understand why DEBUG output appears"""
import requests
import json
import uuid

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

def verify_v3():
    print("🔍 Verifying V3 Deployment Status\n")
    
    # First, let's make a request and analyze the response pattern
    restaurant_id = "bella_vista_restaurant"
    client_id = str(uuid.uuid4())
    
    # Test 1: Simple request that should use no_tool_needed
    print("Test 1: Simple greeting (should be fastest with V3)")
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={
            "restaurant_id": restaurant_id,
            "client_id": client_id,
            "message": "Hi",
            "sender_type": "customer"
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get('answer', '')
        
        # Analyze response structure
        print(f"Response length: {len(answer)}")
        print(f"Contains DEBUG: {'Yes' if '[DEBUG:' in answer else 'No'}")
        print(f"Response ID: {data.get('response_id', 'None')}")
        print(f"Confidence: {data.get('confidence_score', 'None')}")
        
        # Extract DEBUG data if present
        if "[DEBUG:" in answer:
            debug_start = answer.find("[DEBUG:")
            debug_data = answer[debug_start:]
            try:
                # Parse the debug JSON
                debug_json_start = debug_data.find("{")
                debug_json_end = debug_data.rfind("}") + 1
                if debug_json_start > -1 and debug_json_end > 0:
                    debug_obj = json.loads(debug_data[debug_json_start:debug_json_end])
                    print(f"\nDEBUG flow detected:")
                    if "flow" in debug_obj:
                        for step in debug_obj["flow"]:
                            print(f"  - {step.get('step', 'unknown')}")
                    print(f"\nThis indicates the system is using a memory/debug service, not V3")
            except:
                pass
                
        # The actual message before DEBUG
        if "[DEBUG:" in answer:
            actual_answer = answer[:answer.find("[DEBUG:")].strip()
        else:
            actual_answer = answer
        
        print(f"\nActual answer: {actual_answer}")
        
    # Test 2: Tool-requiring request
    print("\n" + "="*60)
    print("Test 2: Tool request (should use V3 tool selection)")
    
    response2 = requests.post(
        f"{BACKEND_URL}/chat",
        json={
            "restaurant_id": restaurant_id,
            "client_id": str(uuid.uuid4()),
            "message": "Show me dishes with truffle",
            "sender_type": "customer"
        }
    )
    
    if response2.status_code == 200:
        data2 = response2.json()
        answer2 = data2.get('answer', '')
        
        print(f"Response length: {len(answer2)}")
        print(f"Contains DEBUG: {'Yes' if '[DEBUG:' in answer2 else 'No'}")
        
        # Check for tool-like responses
        if "truffle" in answer2.lower():
            print("✅ Found truffle-related content")
        
        if any(price in answer2 for price in ["$", "price", ".99"]):
            print("✅ Contains pricing information")
            
    print("\n" + "="*60)
    print("\nConclusion:")
    print("If DEBUG output is present, the system is NOT using internal_tools_v3")
    print("The DEBUG flow suggests a memory/diagnostic service is active instead")
    print("This could be because:")
    print("1. The restaurant's rag_mode wasn't properly updated")
    print("2. A default or fallback service is overriding the setting")
    print("3. The deployment is using a different configuration")

if __name__ == "__main__":
    verify_v3()