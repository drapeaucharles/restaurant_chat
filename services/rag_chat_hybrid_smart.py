"""
Smart Hybrid RAG Service - Automatically switches between optimized and enhanced modes
Uses optimized for simple queries, enhanced for complex ones
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse
from services.rag_chat_optimized import optimized_rag_service
from services.rag_chat_enhanced_v2 import enhanced_rag_service_v2
from services.mia_chat_service_hybrid import detect_language
import re

logger = logging.getLogger(__name__)

class SmartHybridRAG:
    """Intelligently routes queries to the appropriate RAG mode"""
    
    def __init__(self):
        self.complexity_indicators = {
            'multi_dietary': [
                r'vegetarian.*(?:but|and|also).*(?:nut|dairy|gluten)',
                r'allergic.*(?:but|and|also)',
                r'(?:can\'t|cannot|don\'t|no).*(?:eat|have).*(?:and|but)',
            ],
            'follow_up': [
                r'^(?:not|but|however|although)',
                r'^(?:what about|how about|and)',
                r'^(?:yes|no|okay).*(?:but|and)',
                r'(?:too|very|extremely|really)\s+(?:spicy|salty|sweet)',
            ],
            'cultural_educational': [
                r'(?:explain|tell me about|what is|how do)',
                r'(?:authentic|traditional|real|proper)',
                r'(?:difference between|compare)',
                r'(?:history|origin|story|background)',
            ],
            'ambiguous': [
                r'^(?:something|anything)\s+(?:good|nice|special|romantic|light)',
                r'(?:recommend|suggest|what should)',
                r'(?:best|favorite|popular|special)',
            ],
            'multi_part': [
                r'(?:and|also|plus).*\?.*(?:and|also|plus)',
                r'\?.*\?',  # Multiple question marks
                r'(?:first|second|third|finally)',
            ],
            'non_food': [
                r'(?:weather|time|location|direction)',
                r'(?:joke|poem|song|story)',
                r'(?:meaning of|philosophy|life)',
                r'(?:dragon|unicorn|alien|robot)',
            ]
        }
        
        # Simple query patterns (use optimized)
        self.simple_patterns = [
            r'^(?:hi|hello|hey|bonjour|ciao|hola)',
            r'^(?:menu|what.*have|show.*dishes)',
            r'^(?:hours|open|closed)',
            r'^(?:phone|number|contact)',
            r'^(?:where|location|address)',
            r'^(?:price|cost|how much)',
            r'^(?:delivery|takeout|pickup)',
            r'^(?:thank|bye|goodbye)',
        ]
    
    def analyze_complexity(self, message: str) -> Dict[str, any]:
        """Analyze query complexity and determine which mode to use"""
        message_lower = message.lower().strip()
        
        # Check if it's a simple query first
        for pattern in self.simple_patterns:
            if re.search(pattern, message_lower):
                return {
                    'is_complex': False,
                    'mode': 'optimized',
                    'reason': 'simple_query',
                    'confidence': 0.9
                }
        
        # Check for complexity indicators
        complexity_score = 0
        detected_types = []
        
        for complexity_type, patterns in self.complexity_indicators.items():
            for pattern in patterns:
                if re.search(pattern, message_lower):
                    complexity_score += 1
                    detected_types.append(complexity_type)
                    break
        
        # Check message length (long questions often need detailed answers)
        if len(message) > 100:
            complexity_score += 1
            detected_types.append('long_query')
        
        # Check for multiple sentences
        if len(re.findall(r'[.!?]', message)) > 1:
            complexity_score += 1
            detected_types.append('multi_sentence')
        
        # Determine mode based on complexity
        if complexity_score >= 2:
            return {
                'is_complex': True,
                'mode': 'enhanced_v2',
                'reason': detected_types,
                'confidence': min(0.9, 0.5 + complexity_score * 0.1)
            }
        elif complexity_score == 1:
            # Borderline case - use enhanced for certain types
            if any(t in detected_types for t in ['multi_dietary', 'cultural_educational', 'follow_up']):
                return {
                    'is_complex': True,
                    'mode': 'enhanced_v2',
                    'reason': detected_types,
                    'confidence': 0.7
                }
        
        return {
            'is_complex': False,
            'mode': 'optimized',
            'reason': 'default',
            'confidence': 0.8
        }
    
    def should_use_memory(self, db: Session, client_id: str, restaurant_id: str) -> bool:
        """Check if we should look at conversation history"""
        # Check if there's recent conversation that might be relevant
        # This is a simplified check - in production, you'd query the chat history
        return False  # For now, we'll implement this later if needed
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process request with smart routing"""
        # Analyze query complexity
        analysis = self.analyze_complexity(req.message)
        
        # Check if we need conversation memory
        if self.should_use_memory(db, req.client_id, req.restaurant_id):
            analysis['mode'] = 'enhanced_v2'
            analysis['reason'] = ['needs_memory']
        
        # Log the routing decision
        logger.info(f"Smart routing: {analysis['mode']} (reason: {analysis.get('reason', 'default')})")
        
        # Route to appropriate service
        if analysis['mode'] == 'enhanced_v2':
            response = enhanced_rag_service_v2(req, db)
            # Add routing info to help monitor
            if hasattr(response, 'metadata'):
                response.metadata = {'mode': 'enhanced_v2', 'reason': analysis['reason']}
        else:
            response = optimized_rag_service(req, db)
            if hasattr(response, 'metadata'):
                response.metadata = {'mode': 'optimized', 'reason': analysis['reason']}
        
        return response

# Singleton instance
smart_hybrid_rag = SmartHybridRAG()

# Example cost calculator
def estimate_hybrid_costs(monthly_queries: int = 10000):
    """Estimate costs with hybrid approach"""
    # Assume 80% simple, 20% complex queries
    simple_queries = int(monthly_queries * 0.8)
    complex_queries = int(monthly_queries * 0.2)
    
    # Costs
    optimized_cost = 0.0018  # per query
    enhanced_cost = 0.006    # per query
    
    total_cost = (simple_queries * optimized_cost) + (complex_queries * enhanced_cost)
    
    print(f"Hybrid Cost Analysis for {monthly_queries:,} queries/month:")
    print(f"- Simple queries (80%): {simple_queries:,} × ${optimized_cost} = ${simple_queries * optimized_cost:.2f}")
    print(f"- Complex queries (20%): {complex_queries:,} × ${enhanced_cost} = ${complex_queries * enhanced_cost:.2f}")
    print(f"- Total monthly cost: ${total_cost:.2f}")
    print(f"- vs All optimized: ${monthly_queries * optimized_cost:.2f}")
    print(f"- vs All enhanced: ${monthly_queries * enhanced_cost:.2f}")
    print(f"- Savings vs all enhanced: ${(monthly_queries * enhanced_cost) - total_cost:.2f} ({((monthly_queries * enhanced_cost) - total_cost) / (monthly_queries * enhanced_cost) * 100:.1f}%)")