"""
Smart Hybrid RAG Service with Conversation Memory
Combines automatic complexity routing with conversation tracking
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse
from services.rag_chat_optimized import optimized_rag_service
from services.rag_chat_enhanced_v3 import enhanced_rag_chat_v3
from services.conversation_memory_enhanced import enhanced_conversation_memory
from services.mia_chat_service_hybrid import detect_language
import re

logger = logging.getLogger(__name__)

class SmartHybridWithMemoryRAG:
    """Intelligently routes queries with full conversation memory support"""
    
    def __init__(self):
        # Reuse complexity patterns from original hybrid_smart
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
            r'^(?:price|cost|how much).*(?:is|are|for)\s+(?:the|a)\s+\w+',  # Price for specific item
            r'^(?:delivery|takeout|pickup)',
            r'^(?:thank|bye|goodbye)',
        ]
        
        # Initialize services
        self.optimized_service = optimized_rag_service
        self.enhanced_service = enhanced_rag_chat_v3  # v3 has memory built-in
        self.memory = enhanced_conversation_memory
    
    def analyze_complexity_with_memory(self, message: str, client_id: str, restaurant_id: str) -> Dict[str, any]:
        """Analyze query complexity considering conversation history"""
        message_lower = message.lower().strip()
        
        # First check conversation memory for context needs
        conversation_history = self.memory.recall(client_id, restaurant_id)
        has_recent_context = len(conversation_history) > 0
        
        # Check if this query references previous conversation
        if has_recent_context and self.memory.should_clarify_context(client_id, restaurant_id, message):
            # This query needs context, use enhanced
            return {
                'is_complex': True,
                'mode': 'enhanced_v3',
                'reason': ['needs_conversation_context'],
                'confidence': 0.9
            }
        
        # Check if it's a simple query first
        for pattern in self.simple_patterns:
            if re.search(pattern, message_lower):
                # Even simple queries might need context
                if has_recent_context and any(word in message_lower for word in ['more', 'another', 'else', 'other']):
                    return {
                        'is_complex': True,
                        'mode': 'enhanced_v3',
                        'reason': ['simple_with_context'],
                        'confidence': 0.8
                    }
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
        
        # Consider conversation history in complexity scoring
        if has_recent_context:
            # Extract topics from history
            topics = self.memory.extract_topics(conversation_history)
            if topics:
                complexity_score += 0.5  # Slight boost for having context
                detected_types.append('has_context')
        
        # Determine mode based on complexity
        if complexity_score >= 2:
            return {
                'is_complex': True,
                'mode': 'enhanced_v3',
                'reason': detected_types,
                'confidence': min(0.9, 0.5 + complexity_score * 0.1)
            }
        elif complexity_score >= 1:
            # Borderline case - use enhanced for certain types
            if any(t in detected_types for t in ['multi_dietary', 'cultural_educational', 'follow_up', 'has_context']):
                return {
                    'is_complex': True,
                    'mode': 'enhanced_v3',
                    'reason': detected_types,
                    'confidence': 0.7
                }
        
        return {
            'is_complex': False,
            'mode': 'optimized',
            'reason': 'default',
            'confidence': 0.8
        }
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process request with smart routing and conversation memory"""
        # Analyze query complexity with memory context
        analysis = self.analyze_complexity_with_memory(
            req.message, req.client_id, req.restaurant_id
        )
        
        # Log the routing decision
        logger.info(f"Smart routing with memory: {analysis['mode']} (reason: {analysis.get('reason', 'default')})")
        
        # Route to appropriate service
        if analysis['mode'] == 'enhanced_v3':
            # Use enhanced service (which has memory built-in)
            response = self.enhanced_service(req, db)
        else:
            # Use optimized service
            response = self.optimized_service(req, db)
            
            # Even with optimized, we should store in memory for future context
            # Extract response text
            response_text = response.answer if hasattr(response, 'answer') else str(response)
            
            # Store in conversation memory
            self.memory.remember(
                req.client_id, req.restaurant_id,
                req.message, response_text,
                {'mode': 'optimized', 'complexity': analysis}
            )
        
        # Add routing info to help monitor
        if hasattr(response, 'metadata'):
            response.metadata = {
                'mode': analysis['mode'], 
                'reason': analysis['reason'],
                'has_memory': True
            }
        
        return response

# Singleton instance
smart_hybrid_memory_rag = SmartHybridWithMemoryRAG()

# Cost calculator for hybrid + memory
def estimate_hybrid_memory_costs(monthly_queries: int = 10000):
    """Estimate costs with hybrid + memory approach"""
    # Assume 70% simple (optimized), 30% complex (enhanced_v3)
    # Slightly more complex due to memory context
    simple_queries = int(monthly_queries * 0.7)
    complex_queries = int(monthly_queries * 0.3)
    
    # Costs
    optimized_cost = 0.0018  # per query
    enhanced_cost = 0.006    # per query
    
    total_cost = (simple_queries * optimized_cost) + (complex_queries * enhanced_cost)
    
    print(f"Hybrid + Memory Cost Analysis for {monthly_queries:,} queries/month:")
    print(f"- Simple queries (70%): {simple_queries:,} × ${optimized_cost} = ${simple_queries * optimized_cost:.2f}")
    print(f"- Complex queries (30%): {complex_queries:,} × ${enhanced_cost} = ${complex_queries * enhanced_cost:.2f}")
    print(f"- Total monthly cost: ${total_cost:.2f}")
    print(f"- vs All optimized: ${monthly_queries * optimized_cost:.2f}")
    print(f"- vs All enhanced: ${monthly_queries * enhanced_cost:.2f}")
    print(f"- Savings vs all enhanced: ${(monthly_queries * enhanced_cost) - total_cost:.2f} ({((monthly_queries * enhanced_cost) - total_cost) / (monthly_queries * enhanced_cost) * 100:.1f}%)")
    print(f"\nKey benefit: Cost-efficient routing WITH full conversation memory!")