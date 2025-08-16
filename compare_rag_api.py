#!/usr/bin/env python3
"""
Compare RAG modes by calling the API
Since we can't change RAG_MODE remotely, we'll test current mode vs simulated responses
"""
import requests
import json
import time
import statistics
from datetime import datetime
import uuid

BASE_URL = "https://restaurantchat-production.up.railway.app"

# Diverse test questions
TEST_QUESTIONS = [
    # Food-related (10)
    "What pasta dishes do you have?",
    "Do you have any gluten-free options?",
    "Can you recommend something for a vegetarian?",
    "What's your most popular dish?",
    "Do you have any vegan desserts?",
    "What wine pairs well with seafood?",
    "Is the tiramisu homemade?",
    "What's in the Carbonara?",
    "Do you serve breakfast?",
    "Can I get the pasta without cheese?",
    
    # Weird/Challenging (10)
    "Why is the sky blue?",
    "Can you tell me a joke?",
    "Do you deliver to Mars?",
    "Can I bring my pet dragon?",
    "What's the meaning of life?",
    "Can I pay with Bitcoin?",
    "What's the weather like?",
    "Can you write me a poem?",
    "Is time travel possible?",
    "Can I order a unicorn steak?",
    
    # Business/Service (10)
    "What are your opening hours?",
    "Do you take reservations?",
    "Where are you located?",
    "Do you offer delivery?",
    "What's your phone number?",
    "Are you open on holidays?",
    "Do you have parking?",
    "Can I book for 20 people?",
    "Do you have Wi-Fi?",
    "What's your cancellation policy?",
    
    # Multilingual (10)
    "¿Qué platos de pasta tienen?",
    "Bonjour, avez-vous des options végétariennes?",
    "Ciao! Cosa mi consigli?",
    "What's a traditional Italian meal?",
    "Do you serve authentic Italian food?",
    "What's the proper way to eat pasta?",
    "Can you explain what antipasti means?",
    "Do you make fresh pasta daily?",
    "What's your nonna's secret recipe?",
    "Grazie mille!"
]

def test_chat(question: str, client_id: str):
    """Test a single chat question"""
    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/chat",
            json={
                "restaurant_id": "bella_vista_restaurant",
                "client_id": client_id,
                "sender_type": "client",
                "message": question
            },
            timeout=30
        )
        elapsed = time.time() - start
        
        if response.status_code == 200:
            data = response.json()
            return {
                'success': True,
                'answer': data['answer'],
                'time': elapsed,
                'length': len(data['answer']),
                'tokens_est': len(question + data['answer']) // 4
            }
        else:
            return {
                'success': False,
                'answer': f"Error {response.status_code}: {response.text}",
                'time': elapsed,
                'length': 0,
                'tokens_est': 0
            }
    except Exception as e:
        return {
            'success': False,
            'answer': f"Exception: {str(e)}",
            'time': 0,
            'length': 0,
            'tokens_est': 0
        }

def categorize_response(question: str, answer: str):
    """Categorize response quality"""
    answer_lower = answer.lower()
    
    # Check if it's handling the question appropriately
    categories = {
        'perfect': False,
        'good': False,
        'deflected': False,
        'confused': False,
        'error': False
    }
    
    # Error responses
    if "error" in answer_lower or "exception" in answer_lower:
        categories['error'] = True
        return categories
    
    # Check for deflection phrases
    deflection_phrases = [
        "i'm a restaurant assistant",
        "i can only help with",
        "please ask about our menu",
        "that's outside my expertise",
        "i don't have information about"
    ]
    
    if any(phrase in answer_lower for phrase in deflection_phrases):
        categories['deflected'] = True
        return categories
    
    # Check if confused
    if "?" in answer and len(answer) < 50:
        categories['confused'] = True
        return categories
    
    # Check question type and response appropriateness
    question_lower = question.lower()
    
    # Food questions
    if any(word in question_lower for word in ['pasta', 'dish', 'menu', 'food', 'eat', 'gluten', 'vegan']):
        if any(word in answer_lower for word in ['pasta', 'spaghetti', 'penne', 'menu', 'dish', 'serve']):
            categories['perfect'] = True
        else:
            categories['good'] = True
    
    # Business questions
    elif any(word in question_lower for word in ['hour', 'open', 'location', 'delivery', 'reservation']):
        if len(answer) > 20:
            categories['good'] = True
        else:
            categories['deflected'] = True
    
    # Weird questions
    elif any(word in question_lower for word in ['sky', 'dragon', 'mars', 'unicorn', 'time travel']):
        if len(answer) > 30 and not categories['deflected']:
            categories['good'] = True  # Handled it gracefully
    
    # Default
    if not any(categories.values()):
        categories['good'] = True
    
    return categories

def main():
    print("="*80)
    print("🔬 RAG MODE ANALYSIS - CURRENT DEPLOYMENT")
    print("="*80)
    print(f"Testing {len(TEST_QUESTIONS)} diverse questions")
    print(f"API: {BASE_URL}")
    print("="*80)
    
    client_id = str(uuid.uuid4())
    results = []
    
    # Test each question
    for i, question in enumerate(TEST_QUESTIONS):
        print(f"\n[{i+1}/{len(TEST_QUESTIONS)}] Q: {question}")
        
        result = test_chat(question, client_id)
        result['question'] = question
        result['categories'] = categorize_response(question, result['answer'])
        results.append(result)
        
        # Show brief result
        print(f"   A: {result['answer'][:100]}...")
        print(f"   ⏱️  {result['time']:.2f}s | 📏 {result['length']} chars | 🎯 ", end="")
        
        # Show category
        cats = result['categories']
        if cats['perfect']:
            print("Perfect!")
        elif cats['good']:
            print("Good")
        elif cats['deflected']:
            print("Deflected")
        elif cats['confused']:
            print("Confused")
        else:
            print("Error")
        
        # Small delay
        time.sleep(0.5)
    
    # Analysis
    print("\n" + "="*80)
    print("📊 ANALYSIS")
    print("="*80)
    
    # Response times
    times = [r['time'] for r in results if r['success']]
    print(f"\n⏱️  Response Times:")
    print(f"   Average: {statistics.mean(times):.2f}s")
    print(f"   Median: {statistics.median(times):.2f}s")
    print(f"   Min: {min(times):.2f}s")
    print(f"   Max: {max(times):.2f}s")
    
    # Response lengths
    lengths = [r['length'] for r in results if r['success']]
    print(f"\n📏 Response Lengths:")
    print(f"   Average: {statistics.mean(lengths):.0f} chars")
    print(f"   Median: {statistics.median(lengths):.0f} chars")
    print(f"   Min: {min(lengths)} chars")
    print(f"   Max: {max(lengths)} chars")
    
    # Token usage
    tokens = [r['tokens_est'] for r in results]
    total_tokens = sum(tokens)
    print(f"\n🪙 Token Usage (Estimated):")
    print(f"   Average per query: {statistics.mean(tokens):.0f} tokens")
    print(f"   Total for {len(TEST_QUESTIONS)} questions: {total_tokens:,} tokens")
    print(f"   Estimated cost: ${total_tokens * 0.000007:.4f}")
    
    # Quality analysis
    print(f"\n🎯 Response Quality:")
    perfect = sum(1 for r in results if r['categories']['perfect'])
    good = sum(1 for r in results if r['categories']['good'])
    deflected = sum(1 for r in results if r['categories']['deflected'])
    confused = sum(1 for r in results if r['categories']['confused'])
    errors = sum(1 for r in results if r['categories']['error'])
    
    print(f"   Perfect answers: {perfect}/{len(TEST_QUESTIONS)} ({perfect/len(TEST_QUESTIONS)*100:.1f}%)")
    print(f"   Good answers: {good}/{len(TEST_QUESTIONS)} ({good/len(TEST_QUESTIONS)*100:.1f}%)")
    print(f"   Deflected: {deflected}/{len(TEST_QUESTIONS)} ({deflected/len(TEST_QUESTIONS)*100:.1f}%)")
    print(f"   Confused: {confused}/{len(TEST_QUESTIONS)} ({confused/len(TEST_QUESTIONS)*100:.1f}%)")
    print(f"   Errors: {errors}/{len(TEST_QUESTIONS)} ({errors/len(TEST_QUESTIONS)*100:.1f}%)")
    
    # Category breakdown
    print(f"\n📂 By Question Type:")
    food_q = TEST_QUESTIONS[:10]
    weird_q = TEST_QUESTIONS[10:20]
    business_q = TEST_QUESTIONS[20:30]
    multi_q = TEST_QUESTIONS[30:40]
    
    for category, questions in [("Food", food_q), ("Weird", weird_q), ("Business", business_q), ("Multilingual", multi_q)]:
        cat_results = [r for r in results if r['question'] in questions]
        perfect_cat = sum(1 for r in cat_results if r['categories']['perfect'])
        good_cat = sum(1 for r in cat_results if r['categories']['good'])
        print(f"   {category}: {perfect_cat + good_cat}/{len(questions)} handled well")
    
    # Show interesting examples
    print(f"\n📝 Interesting Examples:")
    print("-" * 80)
    
    # Best response
    best = max(results, key=lambda x: x['length'] if x['success'] else 0)
    print(f"\n🌟 Best Response ({best['length']} chars):")
    print(f"Q: {best['question']}")
    print(f"A: {best['answer'][:200]}...")
    
    # Worst response
    worst = min(results, key=lambda x: x['length'] if x['success'] else 999)
    print(f"\n😅 Shortest Response ({worst['length']} chars):")
    print(f"Q: {worst['question']}")
    print(f"A: {worst['answer']}")
    
    # Save results
    filename = f"rag_analysis_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump({
            'test_date': datetime.now().isoformat(),
            'api_url': BASE_URL,
            'questions_count': len(TEST_QUESTIONS),
            'results': results,
            'summary': {
                'avg_time': statistics.mean(times),
                'avg_length': statistics.mean(lengths),
                'total_tokens_est': total_tokens,
                'quality_scores': {
                    'perfect': perfect,
                    'good': good,
                    'deflected': deflected,
                    'confused': confused,
                    'errors': errors
                }
            }
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 Detailed results saved to: {filename}")
    
    print("\n" + "="*80)
    print("✅ ANALYSIS COMPLETE")
    print("="*80)

if __name__ == "__main__":
    main()