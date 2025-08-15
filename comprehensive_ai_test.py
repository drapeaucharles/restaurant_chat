"""
Comprehensive AI Testing - 30 Questions Analysis
"""
import requests
import json
import time
from datetime import datetime
from typing import Dict, List

# API endpoint
BASE_URL = "https://mia-chat-backend-production.up.railway.app"

# Menu data for reference (50 items total)
ACTUAL_MENU = {
    "Appetizers": [
        {"name": "Truffle Arancini", "price": "$12.99"},
        {"name": "Caprese Skewers", "price": "$10.99"},
        {"name": "Calamari Fritti", "price": "$14.99"},
        {"name": "Bruschetta Trio", "price": "$11.99"},
        {"name": "Stuffed Mushrooms", "price": "$13.99"},
        {"name": "Shrimp Cocktail", "price": "$16.99"},
        {"name": "Spinach Artichoke Dip", "price": "$12.99"},
        {"name": "Beef Carpaccio", "price": "$18.99"},
        {"name": "Mezze Platter", "price": "$15.99"},
        {"name": "Oysters Rockefeller", "price": "$19.99"}
    ],
    "Soups & Salads": [
        {"name": "French Onion Soup", "price": "$9.99"},
        {"name": "Lobster Bisque", "price": "$14.99"},
        {"name": "Caesar Salad", "price": "$11.99"},
        {"name": "Greek Salad", "price": "$12.99"},
        {"name": "Roasted Beet Salad", "price": "$13.99"},
        {"name": "Minestrone Soup", "price": "$8.99"},
        {"name": "Quinoa Power Bowl", "price": "$14.99"},
        {"name": "Tom Yum Soup", "price": "$12.99"}
    ],
    "Pasta & Risotto": [
        {"name": "Spaghetti Carbonara", "price": "$18.99"},
        {"name": "Lobster Ravioli", "price": "$28.99"},
        {"name": "Mushroom Risotto", "price": "$22.99"},
        {"name": "Penne Arrabbiata", "price": "$16.99"},
        {"name": "Seafood Linguine", "price": "$32.99"},
        {"name": "Gnocchi Gorgonzola", "price": "$19.99"},
        {"name": "Lasagna Bolognese", "price": "$20.99"},
        {"name": "Saffron Risotto", "price": "$24.99"}
    ],
    "Meat": [
        {"name": "Filet Mignon", "price": "$45.99"},
        {"name": "Rack of Lamb", "price": "$42.99"},
        {"name": "Osso Buco", "price": "$38.99"},
        {"name": "Duck Confit", "price": "$36.99"},
        {"name": "Beef Short Ribs", "price": "$34.99"},
        {"name": "Pork Tenderloin", "price": "$28.99"},
        {"name": "Veal Piccata", "price": "$32.99"},
        {"name": "Ribeye Steak", "price": "$39.99"}
    ],
    "Seafood": [
        {"name": "Grilled Salmon", "price": "$26.99"},
        {"name": "Sea Bass", "price": "$32.99"},
        {"name": "Lobster Thermidor", "price": "$48.99"},
        {"name": "Seared Scallops", "price": "$36.99"},
        {"name": "Tuna Steak", "price": "$34.99"},
        {"name": "Mixed Seafood Grill", "price": "$42.99"}
    ],
    "Vegetarian": [
        {"name": "Eggplant Parmigiana", "price": "$18.99"},
        {"name": "Vegetable Curry", "price": "$16.99"},
        {"name": "Stuffed Bell Peppers", "price": "$17.99"},
        {"name": "Mushroom Wellington", "price": "$22.99"},
        {"name": "Buddha Bowl", "price": "$15.99"}
    ],
    "Desserts": [
        {"name": "Tiramisu", "price": "$9.99"},
        {"name": "Chocolate Lava Cake", "price": "$10.99"},
        {"name": "Crème Brûlée", "price": "$8.99"},
        {"name": "New York Cheesecake", "price": "$9.99"},
        {"name": "Gelato Trio", "price": "$7.99"}
    ]
}

# 30 Test Questions covering various scenarios
TEST_QUESTIONS = [
    # Basic menu queries (1-5)
    {"q": "What pasta dishes do you have?", "category": "menu_overview"},
    {"q": "Show me your menu", "category": "general_menu"},
    {"q": "What's on the menu?", "category": "general_menu"},
    {"q": "List all your dishes", "category": "full_menu"},
    {"q": "What food do you serve?", "category": "general_inquiry"},
    
    # Specific item queries (6-10)
    {"q": "Tell me about the Lobster Ravioli", "category": "specific_item"},
    {"q": "What's in the Spaghetti Carbonara?", "category": "specific_item"},
    {"q": "Describe the Margherita Pizza", "category": "specific_item"},
    {"q": "What comes with the Caesar Salad?", "category": "specific_item"},
    {"q": "How is the Gnocchi Gorgonzola prepared?", "category": "specific_item"},
    
    # Price queries (11-15)
    {"q": "How much is the Lobster Ravioli?", "category": "price"},
    {"q": "What's the price of your pizza?", "category": "price"},
    {"q": "What's your cheapest pasta?", "category": "price_comparison"},
    {"q": "What's the most expensive dish?", "category": "price_comparison"},
    {"q": "Show me dishes under $20", "category": "price_filter"},
    
    # Dietary/ingredient queries (16-20)
    {"q": "Do you have vegetarian options?", "category": "dietary"},
    {"q": "Which dishes have seafood?", "category": "ingredient"},
    {"q": "Do you have any spicy dishes?", "category": "taste_preference"},
    {"q": "What dishes have cheese?", "category": "ingredient"},
    {"q": "Are there any nut allergies I should know about?", "category": "allergy"},
    
    # Non-existent items (21-25)
    {"q": "Do you have sushi?", "category": "non_existent"},
    {"q": "Can I get a burger?", "category": "non_existent"},
    {"q": "Do you serve tacos?", "category": "non_existent"},
    {"q": "Is there any risotto?", "category": "non_existent"},
    {"q": "Do you have French onion soup?", "category": "non_existent"},
    
    # Recommendations (26-30)
    {"q": "What do you recommend?", "category": "recommendation"},
    {"q": "What's popular here?", "category": "recommendation"},
    {"q": "I'm very hungry, what should I get?", "category": "recommendation"},
    {"q": "What's good for a date night?", "category": "recommendation"},
    {"q": "What's your signature dish?", "category": "recommendation"}
]

def test_chat_response(message: str) -> Dict:
    """Send a chat message and get response with timing"""
    start_time = time.time()
    
    payload = {
        "restaurant_id": "bella_vista_restaurant",
        "client_id": "comprehensive-test-client",
        "sender_type": "user",
        "message": message
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/chat_enhanced",
            json=payload,
            timeout=30
        )
        
        elapsed_time = time.time() - start_time
        
        if response.status_code == 200:
            return {
                "success": True,
                "answer": response.json().get("answer", ""),
                "time": elapsed_time,
                "status_code": response.status_code
            }
        else:
            return {
                "success": False,
                "answer": f"Error: {response.status_code} - {response.text}",
                "time": elapsed_time,
                "status_code": response.status_code
            }
    except Exception as e:
        return {
            "success": False,
            "answer": f"Exception: {str(e)}",
            "time": time.time() - start_time,
            "status_code": 0
        }

def analyze_response(question: str, response: Dict, category: str) -> Dict:
    """Analyze response quality and accuracy"""
    analysis = {
        "question": question,
        "category": category,
        "response": response["answer"][:200] + "..." if len(response["answer"]) > 200 else response["answer"],
        "response_time": response["time"],
        "success": response["success"],
        "score": 0,
        "issues": [],
        "positives": [],
        "improvements": []
    }
    
    if not response["success"]:
        analysis["score"] = 0
        analysis["issues"].append("Failed to get response")
        return analysis
    
    answer = response["answer"].lower()
    
    # Category-specific analysis
    if category == "menu_overview":
        # Should list multiple pasta dishes
        pasta_count = sum(1 for pasta in ACTUAL_MENU["Pasta & Risotto"] if pasta["name"].lower() in answer)
        if pasta_count >= 4:
            analysis["score"] += 3
            analysis["positives"].append(f"Listed {pasta_count} pasta/risotto dishes")
        else:
            analysis["issues"].append(f"Only listed {pasta_count} pasta dishes")
            analysis["improvements"].append("Should list at least 4-5 pasta options")
        
        # Check for hallucinations
        non_pasta_items = ["caesar salad", "greek salad", "truffle arancini", "filet mignon"]
        hallucinated = [item for item in non_pasta_items if item in answer]
        if hallucinated:
            analysis["issues"].append(f"Mentioned non-pasta items: {hallucinated}")
            analysis["improvements"].append("Should filter by category accurately")
        else:
            analysis["score"] += 2
            analysis["positives"].append("Correctly filtered pasta items only")
    
    elif category == "specific_item":
        # Should provide accurate details
        item_mentioned = any(item in question.lower() for item in ["lobster ravioli", "carbonara", "margherita", "caesar salad", "gnocchi"])
        if item_mentioned:
            # Check price accuracy
            correct_price = False
            for cat_items in ACTUAL_MENU.values():
                for item in cat_items:
                    if item["name"].lower() in question.lower() and item["price"] in response["answer"]:
                        correct_price = True
                        break
            
            if correct_price:
                analysis["score"] += 3
                analysis["positives"].append("Mentioned correct price")
            else:
                analysis["issues"].append("Price missing or incorrect")
            
            # Check description
            if len(response["answer"]) > 50:
                analysis["score"] += 2
                analysis["positives"].append("Provided detailed description")
            else:
                analysis["improvements"].append("Could provide more detailed description")
    
    elif category == "price":
        # Should mention exact price
        has_price = "$" in response["answer"]
        if has_price:
            analysis["score"] += 5
            analysis["positives"].append("Provided specific price")
        else:
            analysis["issues"].append("No price mentioned")
            analysis["improvements"].append("Must include specific price when asked")
    
    elif category == "non_existent":
        # Should politely decline
        decline_phrases = ["don't have", "not available", "don't serve", "no sushi", "no burger", "no tacos"]
        if any(phrase in answer for phrase in decline_phrases):
            analysis["score"] += 4
            analysis["positives"].append("Correctly stated item not available")
        else:
            analysis["issues"].append("May have hallucinated non-existent item")
        
        # Should not invent items
        if "$" in response["answer"]:
            analysis["issues"].append("Mentioned price for non-existent item")
            analysis["score"] -= 2
        else:
            analysis["score"] += 1
            analysis["positives"].append("Didn't invent prices")
    
    elif category == "dietary":
        # Should identify vegetarian options correctly
        veg_items = ["margherita pizza", "caesar salad", "penne arrabbiata", "gnocchi gorgonzola"]
        veg_mentioned = sum(1 for item in veg_items if item in answer)
        if veg_mentioned >= 2:
            analysis["score"] += 5
            analysis["positives"].append(f"Identified {veg_mentioned} vegetarian options")
        else:
            analysis["improvements"].append("Should identify more vegetarian options")
    
    # General scoring adjustments
    # Response length appropriateness
    if category in ["price", "non_existent"] and len(response["answer"]) < 100:
        analysis["score"] += 1
        analysis["positives"].append("Appropriately concise response")
    elif category in ["menu_overview", "recommendation"] and len(response["answer"]) > 150:
        analysis["score"] += 1
        analysis["positives"].append("Comprehensive response")
    
    # Response time
    if response["time"] < 3:
        analysis["positives"].append(f"Fast response ({response['time']:.1f}s)")
    elif response["time"] > 10:
        analysis["issues"].append(f"Slow response ({response['time']:.1f}s)")
    
    # Cap score at 10
    analysis["score"] = min(10, max(0, analysis["score"]))
    
    return analysis

def generate_report(analyses: List[Dict]):
    """Generate comprehensive report"""
    total_score = sum(a["score"] for a in analyses)
    avg_score = total_score / len(analyses)
    avg_time = sum(a["response_time"] for a in analyses) / len(analyses)
    
    report = f"""
# Comprehensive AI Test Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Overall Performance
- **Total Questions:** {len(analyses)}
- **Average Score:** {avg_score:.1f}/10
- **Total Score:** {total_score}/{len(analyses)*10}
- **Average Response Time:** {avg_time:.2f} seconds
- **Success Rate:** {sum(1 for a in analyses if a["success"])}/{len(analyses)}

## Category Breakdown
"""
    
    # Group by category
    categories = {}
    for analysis in analyses:
        cat = analysis["category"]
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(analysis)
    
    for cat, items in categories.items():
        cat_avg = sum(item["score"] for item in items) / len(items)
        report += f"\n### {cat.replace('_', ' ').title()} (Avg: {cat_avg:.1f}/10)\n"
        
        for item in items:
            report += f"\n**Q: {item['question']}**\n"
            report += f"- Score: {item['score']}/10\n"
            report += f"- Response: {item['response']}\n"
            
            if item['positives']:
                report += f"- ✅ Positives: {', '.join(item['positives'])}\n"
            if item['issues']:
                report += f"- ❌ Issues: {', '.join(item['issues'])}\n"
            if item['improvements']:
                report += f"- 💡 Improvements: {', '.join(item['improvements'])}\n"
    
    # Common issues summary
    all_issues = []
    all_improvements = []
    for a in analyses:
        all_issues.extend(a['issues'])
        all_improvements.extend(a['improvements'])
    
    report += "\n## Common Issues\n"
    issue_counts = {}
    for issue in all_issues:
        issue_counts[issue] = issue_counts.get(issue, 0) + 1
    
    for issue, count in sorted(issue_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        report += f"- {issue} ({count} times)\n"
    
    report += "\n## Recommended Improvements\n"
    improvement_counts = {}
    for imp in all_improvements:
        improvement_counts[imp] = improvement_counts.get(imp, 0) + 1
    
    for imp, count in sorted(improvement_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        report += f"- {imp} ({count} times)\n"
    
    report += "\n## My Recommendations\n"
    report += "1. **Better Category Filtering**: Ensure pasta queries only return pasta items\n"
    report += "2. **Complete Listings**: Show at least 5-6 items when asked for category overview\n"
    report += "3. **Price Accuracy**: Always include exact prices when asked\n"
    report += "4. **Appropriate Length**: Match response length to query type\n"
    report += "5. **No Hallucinations**: Never mention items not in the database\n"
    
    return report

def run_comprehensive_test():
    """Run all 30 tests"""
    print("Starting Comprehensive AI Test...")
    print("=" * 60)
    
    analyses = []
    
    for i, test in enumerate(TEST_QUESTIONS):
        print(f"\nTest {i+1}/30: {test['q']}")
        
        response = test_chat_response(test['q'])
        analysis = analyze_response(test['q'], response, test['category'])
        analyses.append(analysis)
        
        print(f"Score: {analysis['score']}/10")
        print(f"Response: {analysis['response'][:100]}...")
        
        # Small delay between tests
        time.sleep(1)
    
    # Generate and save report
    report = generate_report(analyses)
    
    with open("ai_test_report.md", "w") as f:
        f.write(report)
    
    print("\n" + "=" * 60)
    print(f"Testing complete! Report saved to ai_test_report.md")
    print(f"Overall average score: {sum(a['score'] for a in analyses) / len(analyses):.1f}/10")

if __name__ == "__main__":
    run_comprehensive_test()