#!/usr/bin/env python3
"""
20-Client Sequential Test Script
Tests the live API with 20 different clients, 2-10 messages per client
One client at a time, one question then one answer to avoid GPU overload
"""

import requests
import uuid
import time
import json
from datetime import datetime

# API Configuration
API_URL = "https://restaurantchat-production.up.railway.app/chat"
RESTAURANT_ID = "bella_vista_restaurant"

# Test scenarios for different clients
TEST_SCENARIOS = [
    # Client 1: Vegetarian pasta (should work now!)
    [
        "Show me vegetarian pasta",
        "What's the price of Penne Arrabbiata?",
        "Is it spicy?"
    ],
    
    # Client 2: Vegan options
    [
        "I'm vegan, what can I eat?",
        "Show me vegan pasta",
        "Any vegan desserts?"
    ],
    
    # Client 3: Gluten-free
    [
        "I have celiac disease, what's safe?",
        "Show me gluten-free pasta",
        "Any gluten-free desserts?"
    ],
    
    # Client 4: Popular items
    [
        "What are your most popular dishes?",
        "Show me popular desserts",
        "What's your signature dish?"
    ],
    
    # Client 5: Pasta vs Risotto
    [
        "Show me pasta dishes",
        "Show me risotto",
        "What's the difference between pasta and risotto?"
    ],
    
    # Client 6: Price queries
    [
        "What's your cheapest dish?",
        "Show me dishes under $15",
        "What's the most expensive item?"
    ],
    
    # Client 7: Allergies
    [
        "I'm allergic to nuts, what's safe?",
        "Show me nut-free pasta",
        "Any nut-free desserts?"
    ],
    
    # Client 8: Specific dishes
    [
        "Do you have Margherita pizza?",
        "Show me pizza options",
        "What toppings do you have?"
    ],
    
    # Client 9: Combined dietary + food type
    [
        "Show me vegetarian pasta that's also gluten-free",
        "I'm vegan, show me pasta",
        "Show me dairy-free desserts"
    ],
    
    # Client 10: Menu exploration
    [
        "Show me the menu",
        "What categories do you have?",
        "Show me appetizers"
    ],
    
    # Client 11: Context follow-up
    [
        "I'm vegetarian",
        "Show me pasta",
        "What about desserts?"
    ],
    
    # Client 12: Complex queries
    [
        "Show me vegetarian pasta under $20",
        "What's the healthiest option?",
        "Show me comfort food"
    ],
    
    # Client 13: Dietary combinations
    [
        "I'm vegetarian and gluten-free",
        "Show me pasta",
        "Any desserts I can have?"
    ],
    
    # Client 14: Specific ingredients
    [
        "Do you have truffle dishes?",
        "Show me mushroom dishes",
        "What about seafood?"
    ],
    
    # Client 15: Meal timing
    [
        "What's good for lunch?",
        "Show me dinner options",
        "Any breakfast items?"
    ],
    
    # Client 16: Regional cuisine
    [
        "Show me Italian dishes",
        "What about Mediterranean food?",
        "Any Asian options?"
    ],
    
    # Client 17: Spice levels
    [
        "Show me spicy dishes",
        "What's mild?",
        "Any hot sauces?"
    ],
    
    # Client 18: Family dining
    [
        "What's good for kids?",
        "Show me family portions",
        "Any sharing plates?"
    ],
    
    # Client 19: Health conscious
    [
        "Show me healthy options",
        "What's low calorie?",
        "Any protein-rich dishes?"
    ],
    
    # Client 20: Special requests
    [
        "I don't like mushrooms",
        "Show me dishes without mushrooms",
        "What else can you recommend?"
    ]
]

def test_client(client_id, messages, client_num):
    """Test a single client with their message sequence"""
    print(f"\n{'='*60}")
    print(f"🧪 CLIENT {client_num}: {client_id}")
    print(f"{'='*60}")
    
    results = {
        "client_id": client_id,
        "client_num": client_num,
        "messages": [],
        "total_messages": len(messages),
        "successful_responses": 0,
        "failed_responses": 0,
        "response_times": [],
        "tools_used": [],
        "issues_found": []
    }
    
    for i, message in enumerate(messages, 1):
        print(f"\n📝 Message {i}/{len(messages)}: {message}")
        
        test_data = {
            'message': message,
            'client_id': client_id,
            'restaurant_id': RESTAURANT_ID
        }
        
        start_time = time.time()
        try:
            response = requests.post(API_URL, json=test_data, timeout=30)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                result = response.json()
                answer = result.get('answer', '')
                
                # Extract debug info if available
                debug_info = None
                if '[DEBUG INFO]' in answer:
                    try:
                        debug_start = answer.find('[DEBUG INFO]')
                        debug_text = answer[debug_start + 12:].strip()
                        debug_info = json.loads(debug_text)
                    except:
                        pass
                
                # Check for issues
                issues = []
                if 'do not have' in answer.lower() and any(keyword in message.lower() for keyword in ['vegetarian', 'vegan', 'pasta', 'pizza']):
                    issues.append("Items not found when they should exist")
                
                if response_time > 20:
                    issues.append(f"Slow response: {response_time:.1f}s")
                
                if not answer.strip():
                    issues.append("Empty response")
                
                # Track tools used
                tools_used = []
                if debug_info and 'phase1_tools_selected' in debug_info:
                    tools_used = [tool['tool'] for tool in debug_info['phase1_tools_selected']]
                
                results["messages"].append({
                    "message": message,
                    "response": answer[:200] + "..." if len(answer) > 200 else answer,
                    "response_time": response_time,
                    "tools_used": tools_used,
                    "issues": issues,
                    "debug_info": debug_info
                })
                
                results["successful_responses"] += 1
                results["response_times"].append(response_time)
                results["tools_used"].extend(tools_used)
                results["issues_found"].extend(issues)
                
                print(f"✅ Response ({response_time:.1f}s): {answer[:100]}...")
                if issues:
                    print(f"⚠️ Issues: {', '.join(issues)}")
                if tools_used:
                    print(f"🔧 Tools: {', '.join(tools_used)}")
                
            else:
                results["messages"].append({
                    "message": message,
                    "response": f"ERROR: {response.status_code}",
                    "response_time": time.time() - start_time,
                    "tools_used": [],
                    "issues": [f"HTTP {response.status_code}"],
                    "debug_info": None
                })
                results["failed_responses"] += 1
                results["issues_found"].append(f"HTTP {response.status_code}")
                print(f"❌ Error: {response.status_code}")
        
        except Exception as e:
            results["messages"].append({
                "message": message,
                "response": f"EXCEPTION: {str(e)}",
                "response_time": time.time() - start_time,
                "tools_used": [],
                "issues": [f"Exception: {str(e)}"],
                "debug_info": None
            })
            results["failed_responses"] += 1
            results["issues_found"].append(f"Exception: {str(e)}")
            print(f"❌ Exception: {str(e)}")
        
        # Wait between messages for the same client
        if i < len(messages):
            time.sleep(2)
    
    # Calculate averages
    if results["response_times"]:
        results["avg_response_time"] = sum(results["response_times"]) / len(results["response_times"])
        results["max_response_time"] = max(results["response_times"])
    else:
        results["avg_response_time"] = 0
        results["max_response_time"] = 0
    
    return results

def main():
    """Run the 20-client sequential test"""
    print("🚀 Starting 20-Client Sequential Test")
    print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 API: {API_URL}")
    print(f"🏪 Restaurant: {RESTAURANT_ID}")
    
    all_results = []
    total_start_time = time.time()
    
    for i, messages in enumerate(TEST_SCENARIOS, 1):
        client_id = str(uuid.uuid4())
        client_results = test_client(client_id, messages, i)
        all_results.append(client_results)
        
        # Wait between clients to avoid overloading GPU
        if i < len(TEST_SCENARIOS):
            print(f"\n⏳ Waiting 5 seconds before next client...")
            time.sleep(5)
    
    total_time = time.time() - total_start_time
    
    # Generate summary report
    print(f"\n{'='*80}")
    print("📊 TEST SUMMARY REPORT")
    print(f"{'='*80}")
    
    total_messages = sum(r["total_messages"] for r in all_results)
    total_successful = sum(r["successful_responses"] for r in all_results)
    total_failed = sum(r["failed_responses"] for r in all_results)
    
    print(f"📈 Overall Statistics:")
    print(f"   • Total clients: {len(all_results)}")
    print(f"   • Total messages: {total_messages}")
    print(f"   • Successful responses: {total_successful}")
    print(f"   • Failed responses: {total_failed}")
    print(f"   • Success rate: {(total_successful/total_messages)*100:.1f}%")
    print(f"   • Total test time: {total_time/60:.1f} minutes")
    
    # Response time analysis
    all_response_times = []
    for result in all_results:
        all_response_times.extend(result["response_times"])
    
    if all_response_times:
        avg_response_time = sum(all_response_times) / len(all_response_times)
        max_response_time = max(all_response_times)
        print(f"   • Average response time: {avg_response_time:.1f}s")
        print(f"   • Max response time: {max_response_time:.1f}s")
    
    # Issues analysis
    all_issues = []
    for result in all_results:
        all_issues.extend(result["issues_found"])
    
    if all_issues:
        print(f"\n⚠️ Issues Found ({len(all_issues)} total):")
        issue_counts = {}
        for issue in all_issues:
            issue_counts[issue] = issue_counts.get(issue, 0) + 1
        
        for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {issue}: {count} times")
    
    # Tool usage analysis
    all_tools = []
    for result in all_results:
        all_tools.extend(result["tools_used"])
    
    if all_tools:
        print(f"\n🔧 Tool Usage:")
        tool_counts = {}
        for tool in all_tools:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1
        
        for tool, count in sorted(tool_counts.items(), key=lambda x: x[1], reverse=True):
            print(f"   • {tool}: {count} times")
    
    # Specific fix verification
    print(f"\n🎯 Fix Verification:")
    
    # Check vegetarian pasta fix
    veg_pasta_tests = [r for r in all_results if any('vegetarian pasta' in msg['message'].lower() for msg in r['messages'])]
    if veg_pasta_tests:
        veg_pasta_success = sum(1 for r in veg_pasta_tests if not any('do not have' in msg['response'].lower() for msg in r['messages']))
        print(f"   • Vegetarian pasta queries: {veg_pasta_success}/{len(veg_pasta_tests)} successful")
    
    # Check combined dietary + food-type
    combined_tests = [r for r in all_results if any('vegetarian' in msg['message'].lower() and 'pasta' in msg['message'].lower() for msg in r['messages'])]
    if combined_tests:
        combined_success = sum(1 for r in combined_tests if not any('do not have' in msg['response'].lower() for msg in r['messages']))
        print(f"   • Combined dietary + food-type: {combined_success}/{len(combined_tests)} successful")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"temporary/test_results_20_clients_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "test_info": {
                "timestamp": timestamp,
                "api_url": API_URL,
                "restaurant_id": RESTAURANT_ID,
                "total_clients": len(all_results),
                "total_messages": total_messages,
                "total_time_minutes": total_time/60
            },
            "summary": {
                "successful_responses": total_successful,
                "failed_responses": total_failed,
                "success_rate": (total_successful/total_messages)*100,
                "avg_response_time": avg_response_time if all_response_times else 0,
                "max_response_time": max_response_time if all_response_times else 0,
                "issues_found": len(all_issues),
                "unique_issues": len(set(all_issues))
            },
            "detailed_results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print(f"✅ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

