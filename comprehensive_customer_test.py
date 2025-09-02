#!/usr/bin/env python3
"""
Comprehensive Customer Test Suite - 40 customers testing all features
Including multilingual support, dietary restrictions, reservations, general inquiries, etc.
"""

import requests
import json
import uuid
import time
import random
from datetime import datetime
from typing import List, Dict, Tuple

BASE_URL = "https://restaurantchat-production.up.railway.app"
RESTAURANT_ID = "bella_vista_restaurant"

# Customer profiles with different testing scenarios
CUSTOMER_PROFILES = [
    # General inquiries (10 customers)
    {
        "name": "Sarah_General",
        "scenario": "general_inquiry",
        "messages": [
            "Hi, what time do you open?",
            "Do you have outdoor seating?",
            "Can I bring my dog?",
            "Thanks!"
        ]
    },
    {
        "name": "Mike_Hours",
        "scenario": "opening_hours",
        "messages": [
            "Are you open on Sundays?",
            "What about holidays?"
        ]
    },
    {
        "name": "Lisa_Location",
        "scenario": "location_info",
        "messages": [
            "Where are you located?",
            "Do you have parking?",
            "Is there valet service?"
        ]
    },
    {
        "name": "Tom_Ambiance",
        "scenario": "restaurant_ambiance",
        "messages": [
            "What's the dress code?",
            "Is it good for a romantic dinner?",
            "Do you have live music?"
        ]
    },
    {
        "name": "Emma_Groups",
        "scenario": "group_dining",
        "messages": [
            "Can you accommodate a party of 20?",
            "Do you have private dining rooms?",
            "What about set menus for groups?"
        ]
    },
    {
        "name": "David_Newbie",
        "scenario": "first_time_visitor",
        "messages": [
            "Hi, I've never been to your restaurant",
            "What do you recommend?",
            "What are your most popular dishes?",
            "Do you have a wine list?"
        ]
    },
    {
        "name": "Rachel_Prices",
        "scenario": "price_inquiry",
        "messages": [
            "What's your price range?",
            "Do you have any lunch specials?",
            "Are there happy hour deals?"
        ]
    },
    {
        "name": "John_Payment",
        "scenario": "payment_methods",
        "messages": [
            "Do you accept credit cards?",
            "What about Apple Pay?",
            "Can we split the bill?"
        ]
    },
    {
        "name": "Anna_Kids",
        "scenario": "family_dining",
        "messages": [
            "Do you have a kids menu?",
            "Are high chairs available?",
            "Is it noisy? I have a baby"
        ]
    },
    {
        "name": "Chris_Quick",
        "scenario": "quick_questions",
        "messages": [
            "Do you do takeout?",
            "How about delivery?"
        ]
    },
    
    # Menu exploration (8 customers)
    {
        "name": "Sophia_Appetizers",
        "scenario": "menu_appetizers",
        "messages": [
            "What appetizers do you have?",
            "Tell me more about the Caprese Skewers",
            "What's in the Mezze Platter?",
            "I'll take the Bruschetta Trio"
        ]
    },
    {
        "name": "Oliver_Pasta",
        "scenario": "menu_pasta",
        "messages": [
            "Show me your pasta dishes",
            "Is the Carbonara authentic?",
            "What's the difference between your pasta sauces?",
            "Can I get the Linguine with extra seafood?"
        ]
    },
    {
        "name": "Mia_Seafood",
        "scenario": "menu_seafood",
        "messages": [
            "I love seafood! What do you have?",
            "Is the fish fresh?",
            "Tell me about the Lobster Thermidor",
            "What's your catch of the day?",
            "How is the Grilled Octopus prepared?"
        ]
    },
    {
        "name": "Lucas_Meat",
        "scenario": "menu_meat",
        "messages": [
            "I want a good steak",
            "How do you cook your ribeye?",
            "What sides come with it?",
            "Can I get it well done?"
        ]
    },
    {
        "name": "Ava_Desserts",
        "scenario": "menu_desserts",
        "messages": [
            "Save room for dessert! What do you have?",
            "Is the Tiramisu made in-house?",
            "Tell me about the Chocolate Lava Cake",
            "Do you have anything with fruit?"
        ]
    },
    {
        "name": "Noah_Wine",
        "scenario": "wine_pairing",
        "messages": [
            "Can you recommend a wine?",
            "What pairs well with the Osso Buco?",
            "Do you have wines by the glass?",
            "What about Italian wines?"
        ]
    },
    {
        "name": "Isabella_Specials",
        "scenario": "daily_specials",
        "messages": [
            "Do you have any specials today?",
            "What's the soup of the day?",
            "Any seasonal items?"
        ]
    },
    {
        "name": "Ethan_Curious",
        "scenario": "ingredient_questions",
        "messages": [
            "What's in the Stuffed Mushrooms?",
            "Is the Minestrone Soup homemade?",
            "Do you use fresh pasta?",
            "Where do you source your ingredients?"
        ]
    },
    
    # Dietary restrictions (7 customers)
    {
        "name": "Vegan_Victoria",
        "scenario": "dietary_vegan",
        "messages": [
            "Hi, I'm vegan",
            "What appetizers can I have?",
            "Any vegan pasta options?",
            "What about desserts?",
            "Can you make the bruschetta without cheese?"
        ]
    },
    {
        "name": "GF_George",
        "scenario": "dietary_gluten_free",
        "messages": [
            "I have celiac disease",
            "What gluten-free options do you have?",
            "Can I get the seafood without breading?",
            "Do you have gluten-free pasta?"
        ]
    },
    {
        "name": "Allergic_Alice",
        "scenario": "dietary_allergies",
        "messages": [
            "I have a severe nut allergy",
            "Which dishes are nut-free?",
            "What about cross-contamination?",
            "Is the pesto made with pine nuts?"
        ]
    },
    {
        "name": "Dairy_Daniel",
        "scenario": "dietary_dairy_free",
        "messages": [
            "I'm lactose intolerant",
            "What can I eat that's dairy-free?",
            "Can you make the risotto without butter?",
            "Any dairy-free desserts?"
        ]
    },
    {
        "name": "Keto_Katherine",
        "scenario": "dietary_keto",
        "messages": [
            "I'm on a keto diet",
            "What low-carb options do you have?",
            "Can I get the steak without the sides?",
            "Do you have cauliflower rice?"
        ]
    },
    {
        "name": "Multi_Marcus",
        "scenario": "dietary_multiple",
        "messages": [
            "I need something vegan AND gluten-free",
            "What are my options?",
            "Can you modify any dishes?",
            "Is the quinoa bowl both vegan and GF?"
        ]
    },
    {
        "name": "Checking_Chelsea",
        "scenario": "dietary_verification",
        "messages": [
            "Is the Caesar Salad vegetarian?",
            "Does the French Onion Soup have meat?",
            "Is there dairy in the tomato sauce?",
            "Can I trust your dietary labels?"
        ]
    },
    
    # Reservations and events (5 customers)
    {
        "name": "Birthday_Blake",
        "scenario": "special_occasion",
        "messages": [
            "I want to book for my wife's birthday",
            "Do you do anything special for birthdays?",
            "Can you put candles on the dessert?",
            "We'll be 6 people on Saturday"
        ]
    },
    {
        "name": "Business_Brianna",
        "scenario": "business_dining",
        "messages": [
            "I need to book a business dinner",
            "Do you have a quiet area?",
            "Can we get a fixed menu for 8 people?",
            "What's your cancellation policy?"
        ]
    },
    {
        "name": "Wedding_William",
        "scenario": "event_planning",
        "messages": [
            "Can you host a rehearsal dinner?",
            "We're looking at 40 guests",
            "Do you have event packages?",
            "Can we customize the menu?",
            "What about decorations?"
        ]
    },
    {
        "name": "LastMin_Laura",
        "scenario": "urgent_reservation",
        "messages": [
            "Do you have a table for tonight?",
            "We're 4 people",
            "What time slots are available?",
            "We're flexible on time"
        ]
    },
    {
        "name": "Romantic_Ryan",
        "scenario": "date_night",
        "messages": [
            "Planning a proposal dinner",
            "Can I request a specific table?",
            "Somewhere private with a view?",
            "Can you help make it special?"
        ]
    },
    
    # Complaints and feedback (3 customers)
    {
        "name": "Unhappy_Uma",
        "scenario": "complaint",
        "messages": [
            "I was there last night",
            "The service was really slow",
            "We waited 45 minutes for our mains",
            "I want to speak to a manager"
        ]
    },
    {
        "name": "Feedback_Frank",
        "scenario": "positive_feedback",
        "messages": [
            "Just wanted to say we had an amazing dinner!",
            "The Osso Buco was perfect",
            "Our server Maria was wonderful",
            "We'll definitely be back!"
        ]
    },
    {
        "name": "Suggest_Sally",
        "scenario": "suggestions",
        "messages": [
            "You should add more vegan options",
            "Have you considered a tasting menu?",
            "The music was a bit loud last time"
        ]
    },
    
    # Multilingual customers (5 customers)
    {
        "name": "French_Francois",
        "scenario": "multilingual_french",
        "messages": [
            "Bonjour, avez-vous une table pour ce soir?",
            "Quels sont vos plats végétariens?",
            "Je voudrais le steak, saignant s'il vous plaît",
            "L'addition, s'il vous plaît"
        ]
    },
    {
        "name": "Spanish_Sofia",
        "scenario": "multilingual_spanish",
        "messages": [
            "Hola, ¿tienen menú en español?",
            "¿Cuáles son las especialidades de la casa?",
            "Soy alérgica a los mariscos",
            "¿Puedo pagar con tarjeta?"
        ]
    },
    {
        "name": "Italian_Giovanni",
        "scenario": "multilingual_italian",
        "messages": [
            "Buongiorno! Avete piatti autentici italiani?",
            "La carbonara è fatta come a Roma?",
            "Vorrei un buon vino rosso italiano",
            "Perfetto, grazie mille!"
        ]
    },
    {
        "name": "German_Greta",
        "scenario": "multilingual_german",
        "messages": [
            "Guten Tag, haben Sie einen Tisch für zwei?",
            "Was können Sie für Vegetarier empfehlen?",
            "Gibt es auch glutenfreie Optionen?",
            "Danke schön!"
        ]
    },
    {
        "name": "Japanese_Yuki",
        "scenario": "multilingual_japanese",
        "messages": [
            "こんにちは、予約できますか？",
            "ベジタリアンメニューはありますか？",
            "おすすめは何ですか？",
            "ありがとうございます"
        ]
    },
    
    # Edge cases and complex scenarios (3 customers)
    {
        "name": "Confused_Carl",
        "scenario": "unclear_requests",
        "messages": [
            "Food?",
            "Something good",
            "Not that",
            "The other thing you mentioned",
            "Actually, tell me more about it"
        ]
    },
    {
        "name": "Detailed_Diana",
        "scenario": "very_specific",
        "messages": [
            "I need the Caprese but with buffalo mozzarella not regular, extra basil, light on the balsamic, and can you add some arugula?",
            "Also, is the balsamic glaze made in-house?",
            "What's the sodium content?",
            "Can I get it as a half portion?"
        ]
    },
    {
        "name": "Chatty_Charles",
        "scenario": "small_talk",
        "messages": [
            "Hi Maria! How's your day going?",
            "I love Italian food, reminds me of my trip to Tuscany",
            "Have you ever been to Italy?",
            "My grandmother used to make the best pasta",
            "Anyway, what do you recommend?",
            "That sounds delicious!",
            "You know what, I'll have that",
            "Thanks for the chat!"
        ]
    }
]

def send_message(client_id: str, message: str) -> Dict:
    """Send a message and return the response"""
    try:
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "client_id": client_id,
                "restaurant_id": RESTAURANT_ID,
                "message": message
            },
            timeout=30
        )
        
        if response.status_code == 200:
            return {
                "success": True,
                "response": response.json().get("answer", ""),
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "response": f"Error: {response.status_code}",
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "response": f"Exception: {str(e)}",
            "status_code": 0
        }

def analyze_conversation(conversation: List[Dict]) -> Dict:
    """Analyze a single conversation for metrics"""
    analysis = {
        "total_messages": len(conversation),
        "successful_responses": sum(1 for msg in conversation if msg.get("response_success", False)),
        "failed_responses": sum(1 for msg in conversation if not msg.get("response_success", False)),
        "avg_response_length": 0,
        "dietary_handled_correctly": None,
        "context_maintained": None,
        "tool_usage_detected": False,
        "language_handled": None,
        "customer_satisfied": None
    }
    
    # Calculate average response length
    response_lengths = [len(msg.get("ai_response", "")) for msg in conversation if msg.get("ai_response")]
    if response_lengths:
        analysis["avg_response_length"] = sum(response_lengths) / len(response_lengths)
    
    # Check for tool usage patterns
    for msg in conversation:
        ai_response = msg.get("ai_response", "").lower()
        if any(phrase in ai_response for phrase in ["here are", "i found", "options include", "we have"]):
            analysis["tool_usage_detected"] = True
            break
    
    # Check dietary handling
    dietary_keywords = ["vegan", "vegetarian", "gluten-free", "dairy-free", "allergy", "keto"]
    dietary_mentioned = any(
        any(keyword in msg.get("customer_message", "").lower() for keyword in dietary_keywords)
        for msg in conversation
    )
    
    if dietary_mentioned:
        # Check if AI avoided unsafe recommendations
        unsafe_patterns = [
            ("vegan", ["cheese", "mozzarella", "meat", "fish"]),
            ("dairy-free", ["cheese", "cream", "butter", "milk"]),
            ("nut", ["almond", "walnut", "peanut", "cashew"])
        ]
        
        violations = []
        for msg in conversation:
            customer_msg = msg.get("customer_message", "").lower()
            ai_response = msg.get("ai_response", "").lower()
            
            for diet, unsafe_words in unsafe_patterns:
                if diet in customer_msg:
                    for unsafe in unsafe_words:
                        if unsafe in ai_response and "without" not in ai_response:
                            violations.append(f"{diet} - {unsafe}")
        
        analysis["dietary_handled_correctly"] = len(violations) == 0
        analysis["dietary_violations"] = violations
    
    # Check context maintenance
    pronouns = ["it", "that", "this", "those", "them"]
    context_messages = []
    for i, msg in enumerate(conversation):
        if any(pronoun in msg.get("customer_message", "").lower().split() for pronoun in pronouns):
            context_messages.append(i)
    
    if context_messages:
        # Check if AI understood the context
        context_handled_well = True
        for idx in context_messages:
            if idx < len(conversation):
                response = conversation[idx].get("ai_response", "").lower()
                if "what" in response and "?" in response:  # AI asking what they mean
                    context_handled_well = False
        analysis["context_maintained"] = context_handled_well
    
    # Detect language
    non_english_chars = {
        "french": ["ç", "é", "è", "ê", "à", "ù"],
        "spanish": ["ñ", "¿", "¡"],
        "italian": ["è", "à", "ù", "ò"],
        "german": ["ä", "ö", "ü", "ß"],
        "japanese": ["あ", "い", "う", "え", "お", "か", "き", "く", "け", "こ"]
    }
    
    for lang, chars in non_english_chars.items():
        if any(
            any(char in msg.get("customer_message", "") for char in chars)
            for msg in conversation
        ):
            analysis["language_handled"] = lang
            break
    
    # Estimate satisfaction
    positive_indicators = ["thank", "great", "perfect", "excellent", "wonderful", "definitely"]
    negative_indicators = ["slow", "wrong", "bad", "terrible", "disappointed", "manager"]
    
    positive_count = sum(
        1 for msg in conversation 
        if any(word in msg.get("customer_message", "").lower() for word in positive_indicators)
    )
    negative_count = sum(
        1 for msg in conversation 
        if any(word in msg.get("customer_message", "").lower() for word in negative_indicators)
    )
    
    if positive_count > negative_count:
        analysis["customer_satisfied"] = True
    elif negative_count > positive_count:
        analysis["customer_satisfied"] = False
    
    return analysis

def run_customer_simulation(customer: Dict) -> Dict:
    """Run a complete conversation for one customer"""
    client_id = str(uuid.uuid4())
    conversation = []
    
    print(f"\n{'='*60}")
    print(f"Customer: {customer['name']} - Scenario: {customer['scenario']}")
    print(f"{'='*60}")
    
    for i, message in enumerate(customer['messages']):
        print(f"\n[{i+1}] Customer: {message}")
        
        # Send message
        result = send_message(client_id, message)
        
        # Store conversation turn
        turn = {
            "turn": i + 1,
            "customer_message": message,
            "ai_response": result["response"],
            "response_success": result["success"],
            "status_code": result["status_code"]
        }
        conversation.append(turn)
        
        # Print response
        print(f"AI: {result['response'][:200]}{'...' if len(result['response']) > 200 else ''}")
        
        # Wait for response to complete before next message
        # This ensures we don't overwhelm the single miner
        print("  [Waiting for response to complete...]")
        time.sleep(5)
    
    # Analyze the conversation
    analysis = analyze_conversation(conversation)
    
    result = {
        "customer": customer,
        "client_id": client_id,
        "conversation": conversation,
        "analysis": analysis,
        "timestamp": datetime.now().isoformat()
    }
    
    # Save to temporary file
    temp_filename = f"/tmp/customer_{customer['name']}.json"
    with open(temp_filename, 'w') as f:
        json.dump(result, f, indent=2)
    print(f"💾 Saved to {temp_filename}")
    
    return result

def generate_report(results: List[Dict]) -> Dict:
    """Generate comprehensive analytics report"""
    report = {
        "test_summary": {
            "total_customers": len(results),
            "total_messages": sum(r["analysis"]["total_messages"] for r in results),
            "timestamp": datetime.now().isoformat()
        },
        "scenario_breakdown": {},
        "dietary_performance": {
            "total_dietary_customers": 0,
            "handled_correctly": 0,
            "violations": []
        },
        "language_support": {},
        "customer_satisfaction": {
            "satisfied": 0,
            "unsatisfied": 0,
            "neutral": 0
        },
        "technical_metrics": {
            "success_rate": 0,
            "avg_response_length": 0,
            "tool_usage_rate": 0,
            "context_maintenance_rate": 0
        },
        "detailed_results": results
    }
    
    # Analyze by scenario
    for result in results:
        scenario = result["customer"]["scenario"]
        if scenario not in report["scenario_breakdown"]:
            report["scenario_breakdown"][scenario] = {
                "count": 0,
                "success_rate": 0,
                "avg_messages": 0
            }
        
        report["scenario_breakdown"][scenario]["count"] += 1
        report["scenario_breakdown"][scenario]["avg_messages"] += result["analysis"]["total_messages"]
    
    # Calculate averages for scenarios
    for scenario in report["scenario_breakdown"]:
        count = report["scenario_breakdown"][scenario]["count"]
        report["scenario_breakdown"][scenario]["avg_messages"] /= count
    
    # Dietary performance
    dietary_results = [r for r in results if r["analysis"]["dietary_handled_correctly"] is not None]
    if dietary_results:
        report["dietary_performance"]["total_dietary_customers"] = len(dietary_results)
        report["dietary_performance"]["handled_correctly"] = sum(
            1 for r in dietary_results if r["analysis"]["dietary_handled_correctly"]
        )
        
        # Collect violations
        for r in dietary_results:
            if not r["analysis"]["dietary_handled_correctly"]:
                report["dietary_performance"]["violations"].extend(
                    r["analysis"].get("dietary_violations", [])
                )
    
    # Language support
    for result in results:
        lang = result["analysis"].get("language_handled")
        if lang:
            if lang not in report["language_support"]:
                report["language_support"][lang] = 0
            report["language_support"][lang] += 1
    
    # Customer satisfaction
    for result in results:
        satisfaction = result["analysis"]["customer_satisfied"]
        if satisfaction is True:
            report["customer_satisfaction"]["satisfied"] += 1
        elif satisfaction is False:
            report["customer_satisfaction"]["unsatisfied"] += 1
        else:
            report["customer_satisfaction"]["neutral"] += 1
    
    # Technical metrics
    total_messages = sum(
        sum(1 for turn in r["conversation"] for _ in [turn])
        for r in results
    )
    successful_messages = sum(
        sum(1 for turn in r["conversation"] if turn["response_success"])
        for r in results
    )
    
    report["technical_metrics"]["success_rate"] = (successful_messages / total_messages * 100) if total_messages > 0 else 0
    
    # Average response length
    all_response_lengths = []
    for result in results:
        for turn in result["conversation"]:
            if turn["ai_response"]:
                all_response_lengths.append(len(turn["ai_response"]))
    
    if all_response_lengths:
        report["technical_metrics"]["avg_response_length"] = sum(all_response_lengths) / len(all_response_lengths)
    
    # Tool usage rate
    tool_usage_count = sum(1 for r in results if r["analysis"]["tool_usage_detected"])
    report["technical_metrics"]["tool_usage_rate"] = (tool_usage_count / len(results) * 100)
    
    # Context maintenance rate
    context_tested = [r for r in results if r["analysis"]["context_maintained"] is not None]
    if context_tested:
        context_maintained = sum(1 for r in context_tested if r["analysis"]["context_maintained"])
        report["technical_metrics"]["context_maintenance_rate"] = (context_maintained / len(context_tested) * 100)
    
    return report

def main():
    """Run the comprehensive test suite"""
    print("🤖 COMPREHENSIVE CUSTOMER TEST SUITE")
    print(f"Testing {len(CUSTOMER_PROFILES)} customer scenarios")
    print(f"Restaurant: {RESTAURANT_ID}")
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    # Check for existing temp files
    import glob
    existing_files = glob.glob("/tmp/customer_*.json")
    loaded_customers = set()
    results = []
    
    if existing_files:
        print(f"\n📁 Found {len(existing_files)} existing temp files")
        for temp_file in existing_files:
            try:
                with open(temp_file, 'r') as f:
                    result = json.load(f)
                    customer_name = result['customer']['name']
                    loaded_customers.add(customer_name)
                    results.append(result)
                    print(f"  ✓ Loaded {customer_name}")
            except Exception as e:
                print(f"  ❌ Error loading {temp_file}: {e}")
    
    # Run tests for remaining customers
    for i, customer in enumerate(CUSTOMER_PROFILES):
        if customer['name'] in loaded_customers:
            print(f"\n[{i+1}/{len(CUSTOMER_PROFILES)}] Skipping {customer['name']} (already completed)")
            continue
            
        print(f"\n[{i+1}/{len(CUSTOMER_PROFILES)}] Testing {customer['name']}...")
        
        try:
            result = run_customer_simulation(customer)
            results.append(result)
            
            # Quick summary
            analysis = result["analysis"]
            print(f"\n✓ Completed: {analysis['successful_responses']}/{analysis['total_messages']} successful")
            
            if analysis["dietary_handled_correctly"] is not None:
                status = "✅" if analysis["dietary_handled_correctly"] else "❌"
                print(f"  Dietary handling: {status}")
            
            if analysis["context_maintained"] is not None:
                status = "✅" if analysis["context_maintained"] else "❌"
                print(f"  Context maintenance: {status}")
            
        except Exception as e:
            print(f"❌ Error testing {customer['name']}: {str(e)}")
            continue
        
        # Add delay between customers
        time.sleep(2)
    
    # Generate report
    print("\n\n" + "="*60)
    print("GENERATING ANALYTICS REPORT...")
    print("="*60)
    
    report = generate_report(results)
    
    # Save full results
    output_file = f"customer_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Full results saved to: {output_file}")
    
    # Also save a combined temp file
    combined_temp = "/tmp/all_customer_results.json"
    with open(combined_temp, 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"💾 Raw results saved to: {combined_temp}")
    
    # Print summary
    print("\n📊 TEST SUMMARY")
    print("="*60)
    print(f"Total Customers: {report['test_summary']['total_customers']}")
    print(f"Total Messages: {report['test_summary']['total_messages']}")
    print(f"Success Rate: {report['technical_metrics']['success_rate']:.1f}%")
    print(f"Avg Response Length: {report['technical_metrics']['avg_response_length']:.0f} chars")
    print(f"Tool Usage Rate: {report['technical_metrics']['tool_usage_rate']:.1f}%")
    print(f"Context Maintenance: {report['technical_metrics']['context_maintenance_rate']:.1f}%")
    
    print("\n🍽️ DIETARY HANDLING")
    print(f"Customers with dietary needs: {report['dietary_performance']['total_dietary_customers']}")
    print(f"Handled correctly: {report['dietary_performance']['handled_correctly']}")
    if report['dietary_performance']['violations']:
        print(f"Violations found: {len(report['dietary_performance']['violations'])}")
    
    print("\n🌍 LANGUAGE SUPPORT")
    for lang, count in report['language_support'].items():
        print(f"{lang.capitalize()}: {count} customers")
    
    print("\n😊 CUSTOMER SATISFACTION")
    print(f"Satisfied: {report['customer_satisfaction']['satisfied']}")
    print(f"Unsatisfied: {report['customer_satisfaction']['unsatisfied']}")
    print(f"Neutral: {report['customer_satisfaction']['neutral']}")
    
    print("\n📈 TOP SCENARIOS")
    sorted_scenarios = sorted(
        report['scenario_breakdown'].items(),
        key=lambda x: x[1]['count'],
        reverse=True
    )[:5]
    
    for scenario, data in sorted_scenarios:
        print(f"{scenario}: {data['count']} customers, avg {data['avg_messages']:.1f} messages")
    
    # Clean up temp files
    print("\n🧹 Cleaning up temp files...")
    for temp_file in glob.glob("/tmp/customer_*.json"):
        try:
            import os
            os.remove(temp_file)
        except:
            pass

if __name__ == "__main__":
    main()