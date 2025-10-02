#!/usr/bin/env python3
"""
Debug visa flow orchestrator step by step
"""
import requests
import json
import time

def test_visa_api_endpoints():
    """Test all visa API endpoints to isolate the issue"""
    print("🔍 Testing Visa API Endpoints...")
    
    endpoints = [
        "/visa/products?business_id=gsi_bali_agency",
        "/visa/leads?business_id=gsi_bali_agency", 
        "/visa/applications?business_id=gsi_bali_agency"
    ]
    
    base_url = "https://restaurantchat-production.up.railway.app"
    
    for endpoint in endpoints:
        try:
            print(f"\n📡 Testing: {endpoint}")
            response = requests.get(f"{base_url}{endpoint}", timeout=10)
            
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                data = response.json()
                print(f"   ✅ Success: {len(data) if isinstance(data, list) else 'object'} items")
            else:
                print(f"   ❌ Error: {response.text[:100]}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")

def test_visa_chat_detailed():
    """Test visa chat with detailed error analysis"""
    print("\n🧪 Testing Visa Chat with Error Analysis...")
    
    test_messages = [
        "I need visa help",
        "Show me visa products", 
        "I want B213 KITAS",
        "What are the requirements?",
        "I am from USA and want to stay 6 months"
    ]
    
    for i, message in enumerate(test_messages, 1):
        print(f"\n📝 Test {i}: '{message}'")
        
        try:
            response = requests.post(
                "https://restaurantchat-production.up.railway.app/chat",
                json={
                    'message': message,
                    'client_id': f'123e4567-e89b-12d3-a456-42661417400{i}',
                    'restaurant_id': 'gsi_bali_agency'
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                
                print(f"   📤 Response: {answer[:150]}...")
                
                # Analyze the response
                if "technical difficulties" in answer.lower():
                    print("   ❌ VISA FLOW ERROR: VisaFlowOrchestrator is failing")
                elif "ask_clarify" in answer or "[DEBUG INFO]" in answer:
                    print("   ❌ ROUTING ERROR: Still using restaurant service")
                elif "visa" in answer.lower() and "technical" not in answer.lower():
                    print("   ✅ VISA RESPONSE: Proper visa service response")
                else:
                    print("   ⚠️ UNCLEAR: Unknown response type")
                    
            else:
                print(f"   ❌ HTTP {response.status_code}: {response.text[:100]}")
                
        except Exception as e:
            print(f"   💥 Exception: {e}")
        
        time.sleep(1)  # Rate limiting

def test_mia_backend_connection():
    """Test if MIA backend is accessible"""
    print("\n🌐 Testing MIA Backend Connection...")
    
    mia_urls = [
        "https://mia-backend-production.up.railway.app",
        "https://mia-backend-production.up.railway.app/health",
        "https://mia-backend-production.up.railway.app/api/health"
    ]
    
    for url in mia_urls:
        try:
            print(f"\n📡 Testing: {url}")
            response = requests.get(url, timeout=10)
            print(f"   Status: {response.status_code}")
            if response.status_code == 200:
                print(f"   ✅ MIA Backend accessible")
            else:
                print(f"   ⚠️ Response: {response.text[:100]}")
        except Exception as e:
            print(f"   ❌ MIA Backend not accessible: {e}")

def test_database_visa_data():
    """Test if visa data is accessible via direct database query simulation"""
    print("\n💾 Testing Visa Data Accessibility...")
    
    # Test via API that should directly query database
    try:
        # This should work if database is properly set up
        response = requests.get(
            "https://restaurantchat-production.up.railway.app/businesses/gsi_bali_agency",
            timeout=10
        )
        
        print(f"Business API Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ GSI Business accessible: {data.get('name', 'unknown')}")
            print(f"   Business Type: {data.get('type', 'unknown')}")
        else:
            print(f"❌ GSI Business not accessible: {response.text[:100]}")
            
    except Exception as e:
        print(f"💥 Business API error: {e}")

def analyze_visa_service_architecture():
    """Analyze what might be wrong with visa service architecture"""
    print("\n🏗️ Analyzing Visa Service Architecture...")
    
    potential_issues = [
        "1. VisaFlowOrchestrator import failing",
        "2. get_visa_tools() returning empty or failing", 
        "3. MIA backend connection timeout",
        "4. Database query errors in visa tools",
        "5. Missing environment variables (MIA_VISA_ENABLED, MIA_BACKEND_URL)",
        "6. Visa flow prompts or logic errors",
        "7. Tool execution errors in visa.v1.* tools"
    ]
    
    print("🔍 Potential Issues to Investigate:")
    for issue in potential_issues:
        print(f"   {issue}")
    
    print("\n🎯 Debugging Strategy:")
    print("   1. Check if visa API endpoints work (database access)")
    print("   2. Check if MIA backend is accessible (external dependency)")
    print("   3. Check if visa tools are properly registered")
    print("   4. Check if flow orchestration logic has bugs")

def main():
    print("🚀 DEBUGGING VISA FLOW ORCHESTRATOR")
    print("=" * 60)
    
    # Step 1: Test visa API endpoints (database layer)
    test_visa_api_endpoints()
    
    # Step 2: Test MIA backend connection (external dependency)
    test_mia_backend_connection()
    
    # Step 3: Test database access via business API
    test_database_visa_data()
    
    # Step 4: Test visa chat with detailed analysis
    test_visa_chat_detailed()
    
    # Step 5: Provide analysis
    analyze_visa_service_architecture()
    
    print("\n" + "=" * 60)
    print("🎯 SUMMARY:")
    print("- If visa APIs fail: Database/table structure issue")
    print("- If MIA backend fails: External dependency issue") 
    print("- If chat gives 'technical difficulties': Flow orchestrator bug")
    print("- If chat uses restaurant tools: Routing still broken")

if __name__ == "__main__":
    main()
