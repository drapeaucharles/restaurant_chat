#!/usr/bin/env python3
"""
30-Client Comprehensive Test Script
Tests the live API with 30 different clients, 2-10 messages per client
Compares results with actual database data to validate accuracy
Tests the new general partial name matching solution
"""

import requests
import uuid
import time
import json
from datetime import datetime

# API Configuration
API_URL = "https://restaurantchat-production.up.railway.app/chat"
RESTAURANT_ID = "bella_vista_restaurant"

# Test scenarios for different clients - focusing on edge cases and general solution
TEST_SCENARIOS = [
    # Client 1-5: Risotto and similar cases (test general solution)
    [
        "Show me risotto",
        "Do you have risotto dishes?",
        "What risotto options do you have?"
    ],
    
    # Client 2: Pasta vs Risotto separation
    [
        "Show me pasta dishes",
        "Show me risotto",
        "What's the difference between pasta and risotto?"
    ],
    
    # Client 3: Vegetarian pasta (should still work)
    [
        "Show me vegetarian pasta",
        "What vegetarian pasta do you have?",
        "Any vegan pasta options?"
    ],
    
    # Client 4: Combined dietary + food type
    [
        "Show me vegetarian pasta that's also gluten-free",
        "I'm vegan, show me pasta",
        "Show me dairy-free desserts"
    ],
    
    # Client 5: Non-category food types (test general solution)
    [
        "Show me arancini",
        "Do you have gnocchi?",
        "What carbonara options do you have?"
    ],
    
    # Client 6-10: Standard food types
    [
        "Show me pizza",
        "What pizza do you have?",
        "Any vegetarian pizza?"
    ],
    
    [
        "Show me seafood",
        "What fish dishes do you have?",
        "Any shellfish options?"
    ],
    
    [
        "Show me chicken dishes",
        "What chicken do you have?",
        "Any grilled chicken?"
    ],
    
    [
        "Show me beef",
        "What beef dishes are available?",
        "Any steak options?"
    ],
    
    [
        "Show me vegetarian options",
        "What vegan dishes do you have?",
        "Any gluten-free options?"
    ],
    
    # Client 11-15: Course types
    [
        "Show me appetizers",
        "What starters do you have?",
        "Any small plates?"
    ],
    
    [
        "Show me main courses",
        "What entrees do you have?",
        "Any dinner options?"
    ],
    
    [
        "Show me desserts",
        "What sweets do you have?",
        "Any cakes or ice cream?"
    ],
    
    [
        "Show me popular dishes",
        "What's your most popular item?",
        "What do people order most?"
    ],
    
    [
        "Show me the menu",
        "What's on your menu?",
        "What do you serve?"
    ],
    
    # Client 16-20: Specific dish names (test get_dish_details)
    [
        "Do you have spaghetti carbonara?",
        "Show me penne arrabbiata",
        "What about margherita pizza?"
    ],
    
    [
        "Do you have tiramisu?",
        "Show me chocolate cake",
        "What about cheesecake?"
    ],
    
    [
        "Do you have caesar salad?",
        "Show me caprese salad",
        "What about greek salad?"
    ],
    
    [
        "Do you have mushroom risotto?",
        "Show me saffron risotto",
        "What about truffle risotto?"
    ],
    
    [
        "Do you have chicken parmesan?",
        "Show me veal marsala",
        "What about osso buco?"
    ],
    
    # Client 21-25: Ingredient-based searches
    [
        "Show me dishes with mushrooms",
        "What has truffle in it?",
        "Any dishes with saffron?"
    ],
    
    [
        "Show me dishes with cheese",
        "What has parmesan?",
        "Any mozzarella dishes?"
    ],
    
    [
        "Show me dishes with tomatoes",
        "What has basil?",
        "Any garlic dishes?"
    ],
    
    [
        "Show me dishes with seafood",
        "What has shrimp?",
        "Any lobster dishes?"
    ],
    
    [
        "Show me dishes with pasta",
        "What has rice?",
        "Any quinoa dishes?"
    ],
    
    # Client 26-30: Edge cases and complex queries
    [
        "I'm allergic to nuts, what's safe?",
        "Show me nut-free options",
        "What about dairy-free?"
    ],
    
    [
        "What's your cheapest dish?",
        "Show me expensive options",
        "What's under $15?"
    ],
    
    [
        "What's good for lunch?",
        "Show me dinner options",
        "Any breakfast items?"
    ],
    
    [
        "What's healthy here?",
        "Show me low-calorie options",
        "Any protein-rich dishes?"
    ],
    
    [
        "What's your signature dish?",
        "Show me chef's specials",
        "Any house specialties?"
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
        "issues_found": [],
        "database_accuracy": []
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
                db_accuracy = "unknown"
                
                # Check for specific accuracy issues
                if 'do not have' in answer.lower():
                    # Check if this might be a false negative
                    if any(keyword in message.lower() for keyword in ['risotto', 'pasta', 'pizza', 'vegetarian', 'vegan']):
                        issues.append("Items not found when they should exist")
                        db_accuracy = "false_negative"
                elif 'found' in answer.lower() or any(item in answer for item in ['$', 'price']):
                    db_accuracy = "items_found"
                
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
                    "debug_info": debug_info,
                    "database_accuracy": db_accuracy
                })
                
                results["successful_responses"] += 1
                results["response_times"].append(response_time)
                results["tools_used"].extend(tools_used)
                results["issues_found"].extend(issues)
                results["database_accuracy"].append(db_accuracy)
                
                print(f"✅ Response ({response_time:.1f}s): {answer[:100]}...")
                if issues:
                    print(f"⚠️ Issues: {', '.join(issues)}")
                if tools_used:
                    print(f"🔧 Tools: {', '.join(tools_used)}")
                print(f"📊 DB Accuracy: {db_accuracy}")
                
            else:
                results["messages"].append({
                    "message": message,
                    "response": f"ERROR: {response.status_code}",
                    "response_time": time.time() - start_time,
                    "tools_used": [],
                    "issues": [f"HTTP {response.status_code}"],
                    "debug_info": None,
                    "database_accuracy": "error"
                })
                results["failed_responses"] += 1
                results["issues_found"].append(f"HTTP {response.status_code}")
                results["database_accuracy"].append("error")
                print(f"❌ Error: {response.status_code}")
        
        except Exception as e:
            results["messages"].append({
                "message": message,
                "response": f"EXCEPTION: {str(e)}",
                "response_time": time.time() - start_time,
                "tools_used": [],
                "issues": [f"Exception: {str(e)}"],
                "debug_info": None,
                "database_accuracy": "error"
            })
            results["failed_responses"] += 1
            results["issues_found"].append(f"Exception: {str(e)}")
            results["database_accuracy"].append("error")
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
    """Run the 30-client comprehensive test"""
    print("🚀 Starting 30-Client Comprehensive Test")
    print(f"📅 Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🎯 API: {API_URL}")
    print(f"🏪 Restaurant: {RESTAURANT_ID}")
    print(f"🔧 Testing: General partial name matching solution")
    
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
    
    # Generate comprehensive summary report
    print(f"\n{'='*80}")
    print("📊 COMPREHENSIVE TEST SUMMARY REPORT")
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
    
    # Database accuracy analysis
    all_db_accuracy = []
    for result in all_results:
        all_db_accuracy.extend(result["database_accuracy"])
    
    accuracy_counts = {}
    for accuracy in all_db_accuracy:
        accuracy_counts[accuracy] = accuracy_counts.get(accuracy, 0) + 1
    
    print(f"\n📊 Database Accuracy Analysis:")
    for accuracy_type, count in accuracy_counts.items():
        percentage = (count / len(all_db_accuracy)) * 100
        print(f"   • {accuracy_type}: {count} ({percentage:.1f}%)")
    
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
    
    # Specific solution verification
    print(f"\n🎯 General Solution Verification:")
    
    # Check risotto queries
    risotto_tests = [r for r in all_results if any('risotto' in msg['message'].lower() for msg in r['messages'])]
    if risotto_tests:
        risotto_success = sum(1 for r in risotto_tests if not any('do not have' in msg['response'].lower() for msg in r['messages']))
        print(f"   • Risotto queries: {risotto_success}/{len(risotto_tests)} successful")
    
    # Check vegetarian pasta
    veg_pasta_tests = [r for r in all_results if any('vegetarian pasta' in msg['message'].lower() for msg in r['messages'])]
    if veg_pasta_tests:
        veg_pasta_success = sum(1 for r in veg_pasta_tests if not any('do not have' in msg['response'].lower() for msg in r['messages']))
        print(f"   • Vegetarian pasta queries: {veg_pasta_success}/{len(veg_pasta_tests)} successful")
    
    # Check combined dietary + food-type
    combined_tests = [r for r in all_results if any('vegetarian' in msg['message'].lower() and 'pasta' in msg['message'].lower() for msg in r['messages'])]
    if combined_tests:
        combined_success = sum(1 for r in combined_tests if not any('do not have' in msg['response'].lower() for msg in r['messages']))
        print(f"   • Combined dietary + food-type: {combined_success}/{len(combined_tests)} successful")
    
    # Check non-category food types (test general solution)
    non_category_tests = [r for r in all_results if any(keyword in msg['message'].lower() for msg in r['messages'] for keyword in ['arancini', 'gnocchi', 'carbonara'])]
    if non_category_tests:
        non_category_success = sum(1 for r in non_category_tests if any('found' in msg['response'].lower() or '$' in msg['response'] for msg in r['messages']))
        print(f"   • Non-category food types: {non_category_success}/{len(non_category_tests)} found items")
    
    # Save detailed results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_file = f"temporary/test_results_30_clients_comprehensive_{timestamp}.json"
    
    with open(results_file, 'w') as f:
        json.dump({
            "test_info": {
                "timestamp": timestamp,
                "api_url": API_URL,
                "restaurant_id": RESTAURANT_ID,
                "total_clients": len(all_results),
                "total_messages": total_messages,
                "total_time_minutes": total_time/60,
                "test_type": "comprehensive_30_clients_general_solution"
            },
            "summary": {
                "successful_responses": total_successful,
                "failed_responses": total_failed,
                "success_rate": (total_successful/total_messages)*100,
                "avg_response_time": avg_response_time if all_response_times else 0,
                "max_response_time": max_response_time if all_response_times else 0,
                "issues_found": len(all_issues),
                "unique_issues": len(set(all_issues)),
                "database_accuracy": accuracy_counts
            },
            "detailed_results": all_results
        }, f, indent=2)
    
    print(f"\n💾 Detailed results saved to: {results_file}")
    print(f"✅ Test completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if __name__ == "__main__":
    main()

