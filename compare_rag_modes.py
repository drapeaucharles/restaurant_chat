#!/usr/bin/env python3
"""
Compare RAG modes: optimized vs enhanced_v2
Tests 100 diverse questions to see quality and token usage differences
"""
import requests
import json
import time
import statistics
from datetime import datetime
import os

# For testing locally, we'll simulate both modes
import sys
sys.path.append('/home/charles-drapeau/Documents/Project/Restaurant/BackEnd')

from database import get_db
from schemas.chat import ChatRequest, ChatResponse
from services.rag_chat_optimized import optimized_rag_service
from services.rag_chat_enhanced_v2 import enhanced_rag_service_v2
import uuid

# Test questions - diverse mix
TEST_QUESTIONS = [
    # Food-related (25)
    "What pasta dishes do you have?",
    "Do you have any gluten-free options?",
    "What's your most expensive dish?",
    "Can you recommend something for a vegetarian?",
    "What ingredients are in the Carbonara?",
    "Do you serve breakfast?",
    "What's good for someone with a nut allergy?",
    "How spicy is the Arrabbiata?",
    "What wine pairs well with seafood?",
    "Do you have any vegan desserts?",
    "What's the chef's special today?",
    "Can I get the pasta without cheese?",
    "What's your most popular dish?",
    "Do you have kids menu?",
    "What fish dishes are available?",
    "Is the tiramisu homemade?",
    "What's in your house salad?",
    "Do you have any dairy-free options?",
    "What's the portion size like?",
    "Can you make the pasta less salty?",
    "What appetizers do you recommend?",
    "Do you have any seasonal specials?",
    "What's the difference between your pizzas?",
    "Is the bread complimentary?",
    "What soups do you have today?",
    
    # Weird/Challenging questions (25)
    "Why is the sky blue?",
    "Can you tell me a joke?",
    "What's the meaning of life?",
    "Do you deliver to Mars?",
    "Can I bring my pet dragon?",
    "What's 2+2?",
    "Tell me about quantum physics",
    "Can I pay with Bitcoin?",
    "Is water wet?",
    "What came first, chicken or egg?",
    "Can you sing me a song?",
    "What's the weather like?",
    "How do I fix my computer?",
    "What's your favorite color?",
    "Can you write me a poem?",
    "Why do we dream?",
    "Is time travel possible?",
    "What's the capital of Atlantis?",
    "Can I order a unicorn steak?",
    "Do you know any magic tricks?",
    "What's inside a black hole?",
    "Can robots feel love?",
    "Why do cats purr?",
    "Is the moon made of cheese?",
    "Can you teach me Italian?",
    
    # Business/Service questions (25)
    "What are your opening hours?",
    "Do you take reservations?",
    "Where are you located?",
    "Do you do catering?",
    "What's your phone number?",
    "Do you have parking?",
    "Are you open on holidays?",
    "Do you accept credit cards?",
    "Can I book for 20 people?",
    "Do you have outdoor seating?",
    "What's your cancellation policy?",
    "Do you offer delivery?",
    "Are you wheelchair accessible?",
    "Do you have Wi-Fi?",
    "Can I see the wine list?",
    "Do you do birthday parties?",
    "What's the dress code?",
    "Do you have live music?",
    "Can I make a special request?",
    "Do you have a loyalty program?",
    "What COVID precautions do you take?",
    "Do you have private dining rooms?",
    "Can I order in advance?",
    "Do you have gift cards?",
    "What's your refund policy?",
    
    # Multilingual/Cultural (25)
    "¿Qué platos de pasta tienen?",
    "Bonjour, avez-vous des options végétariennes?",
    "Ciao! Cosa mi consigli?",
    "What's a traditional Italian meal?",
    "Do you serve authentic Italian food?",
    "What's the difference between Romano and Parmesan?",
    "Can you explain what antipasti means?",
    "What makes your pizza Neapolitan style?",
    "Do you import ingredients from Italy?",
    "What's the proper way to eat pasta?",
    "Can you recommend a good Chianti?",
    "What's your nonna's secret recipe?",
    "Do you make fresh pasta daily?",
    "What region of Italy is your chef from?",
    "Can you teach me some Italian food words?",
    "What's the difference between risotto and rice?",
    "Do you have any Sicilian dishes?",
    "What makes good olive oil?",
    "Can you explain the cheese course?",
    "What's a typical Italian breakfast?",
    "Do you serve aperitivos?",
    "What's the story behind tiramisu?",
    "Can I have my coffee before dessert?",
    "What herbs do you grow?",
    "Is your tomato sauce San Marzano?"
]

class RAGComparator:
    def __init__(self):
        self.results = {
            'optimized': [],
            'enhanced_v2': []
        }
        self.restaurant_id = "bella_vista_restaurant"
        self.client_id = str(uuid.uuid4())
        
    def test_question_locally(self, question: str, db):
        """Test a question with both services locally"""
        results = {}
        
        # Create request
        req = ChatRequest(
            restaurant_id=self.restaurant_id,
            client_id=self.client_id,
            sender_type="client",
            message=question
        )
        
        # Test optimized mode
        try:
            start = time.time()
            response_opt = optimized_rag_service(req, db)
            time_opt = time.time() - start
            
            results['optimized'] = {
                'answer': response_opt.answer,
                'time': time_opt,
                'length': len(response_opt.answer),
                'tokens_est': len(question + response_opt.answer) // 4
            }
        except Exception as e:
            results['optimized'] = {
                'answer': f"Error: {str(e)}",
                'time': 0,
                'length': 0,
                'tokens_est': 0
            }
        
        # Test enhanced_v2 mode
        try:
            start = time.time()
            response_enh = enhanced_rag_service_v2(req, db)
            time_enh = time.time() - start
            
            results['enhanced_v2'] = {
                'answer': response_enh.answer,
                'time': time_enh,
                'length': len(response_enh.answer),
                'tokens_est': len(question + response_enh.answer) // 4 + 200  # Extra for context
            }
        except Exception as e:
            results['enhanced_v2'] = {
                'answer': f"Error: {str(e)}",
                'time': 0,
                'length': 0,
                'tokens_est': 0
            }
        
        return results
    
    def run_comparison(self, questions: list):
        """Run comparison on all questions"""
        db = next(get_db())
        
        print(f"🧪 Testing {len(questions)} questions with both RAG modes...\n")
        
        for i, question in enumerate(questions):
            print(f"[{i+1}/{len(questions)}] Testing: {question[:50]}...")
            
            results = self.test_question_locally(question, db)
            
            # Store results
            for mode in ['optimized', 'enhanced_v2']:
                self.results[mode].append({
                    'question': question,
                    'answer': results[mode]['answer'],
                    'time': results[mode]['time'],
                    'length': results[mode]['length'],
                    'tokens_est': results[mode]['tokens_est']
                })
            
            # Brief comparison
            print(f"  ⚡ Optimized: {results['optimized']['length']} chars, {results['optimized']['time']:.2f}s")
            print(f"  🌟 Enhanced: {results['enhanced_v2']['length']} chars, {results['enhanced_v2']['time']:.2f}s")
            
            # Small delay to avoid overwhelming
            time.sleep(0.1)
        
        print("\n✅ Testing complete!")
        db.close()
    
    def analyze_results(self):
        """Analyze and compare results"""
        print("\n" + "="*80)
        print("📊 COMPREHENSIVE ANALYSIS")
        print("="*80)
        
        for mode in ['optimized', 'enhanced_v2']:
            results = self.results[mode]
            
            # Calculate statistics
            times = [r['time'] for r in results]
            lengths = [r['length'] for r in results]
            tokens = [r['tokens_est'] for r in results]
            
            print(f"\n{'⚡ OPTIMIZED MODE' if mode == 'optimized' else '🌟 ENHANCED V2 MODE'}")
            print("-" * 40)
            print(f"Average response time: {statistics.mean(times):.3f}s")
            print(f"Average response length: {statistics.mean(lengths):.0f} chars")
            print(f"Average tokens (est): {statistics.mean(tokens):.0f}")
            print(f"Total tokens (est): {sum(tokens):,}")
            print(f"Estimated cost (100 questions): ${sum(tokens) * 0.000007:.2f}")
            
            # Quality metrics
            errors = sum(1 for r in results if "Error:" in r['answer'])
            short_answers = sum(1 for r in results if len(r['answer']) < 20)
            
            print(f"Errors: {errors}")
            print(f"Very short answers: {short_answers}")
        
        # Direct comparison
        print("\n" + "="*80)
        print("🔍 DIRECT COMPARISON")
        print("="*80)
        
        better_quality = 0
        same_quality = 0
        worse_quality = 0
        
        for i in range(len(TEST_QUESTIONS)):
            opt = self.results['optimized'][i]
            enh = self.results['enhanced_v2'][i]
            
            # Simple quality comparison based on length and errors
            opt_quality = 0 if "Error:" in opt['answer'] else len(opt['answer'])
            enh_quality = 0 if "Error:" in enh['answer'] else len(enh['answer'])
            
            if enh_quality > opt_quality * 1.2:  # 20% more content
                better_quality += 1
            elif opt_quality > enh_quality * 1.2:
                worse_quality += 1
            else:
                same_quality += 1
        
        print(f"Enhanced V2 gave better answers: {better_quality}/{len(TEST_QUESTIONS)}")
        print(f"Similar quality answers: {same_quality}/{len(TEST_QUESTIONS)}")
        print(f"Optimized gave better answers: {worse_quality}/{len(TEST_QUESTIONS)}")
        
        # Show some interesting examples
        print("\n" + "="*80)
        print("📝 INTERESTING EXAMPLES")
        print("="*80)
        
        # Find questions with biggest differences
        differences = []
        for i in range(len(TEST_QUESTIONS)):
            opt = self.results['optimized'][i]
            enh = self.results['enhanced_v2'][i]
            diff = abs(len(enh['answer']) - len(opt['answer']))
            differences.append((i, diff))
        
        differences.sort(key=lambda x: x[1], reverse=True)
        
        # Show top 5 differences
        for idx, diff in differences[:5]:
            question = TEST_QUESTIONS[idx]
            opt_answer = self.results['optimized'][idx]['answer']
            enh_answer = self.results['enhanced_v2'][idx]['answer']
            
            print(f"\n❓ Question: {question}")
            print(f"\n⚡ Optimized ({len(opt_answer)} chars):")
            print(f"   {opt_answer[:150]}...")
            print(f"\n🌟 Enhanced V2 ({len(enh_answer)} chars):")
            print(f"   {enh_answer[:150]}...")
            print("-" * 80)
        
        # Save detailed results
        self.save_results()
    
    def save_results(self):
        """Save detailed results to file"""
        filename = f"rag_comparison_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump({
                'test_date': datetime.now().isoformat(),
                'questions_count': len(TEST_QUESTIONS),
                'results': self.results,
                'summary': {
                    'optimized': {
                        'avg_time': statistics.mean([r['time'] for r in self.results['optimized']]),
                        'avg_length': statistics.mean([r['length'] for r in self.results['optimized']]),
                        'avg_tokens': statistics.mean([r['tokens_est'] for r in self.results['optimized']]),
                        'total_cost_est': sum([r['tokens_est'] for r in self.results['optimized']]) * 0.000007
                    },
                    'enhanced_v2': {
                        'avg_time': statistics.mean([r['time'] for r in self.results['enhanced_v2']]),
                        'avg_length': statistics.mean([r['length'] for r in self.results['enhanced_v2']]),
                        'avg_tokens': statistics.mean([r['tokens_est'] for r in self.results['enhanced_v2']]),
                        'total_cost_est': sum([r['tokens_est'] for r in self.results['enhanced_v2']]) * 0.000007
                    }
                }
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n💾 Detailed results saved to: {filename}")

def main():
    print("="*80)
    print("🔬 RAG MODE COMPARISON TEST")
    print("="*80)
    print(f"Testing {len(TEST_QUESTIONS)} diverse questions")
    print("Comparing: optimized vs enhanced_v2")
    print("="*80)
    
    comparator = RAGComparator()
    comparator.run_comparison(TEST_QUESTIONS)
    comparator.analyze_results()

if __name__ == "__main__":
    main()