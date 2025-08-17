"""
Smart Hybrid RAG Service with Conversation Memory V2
Improved handling of personal interactions and context
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse
from services.rag_chat_optimized import optimized_rag_service
from services.rag_chat_enhanced_v3 import enhanced_rag_chat_v3
from services.conversation_memory_enhanced_fixed import enhanced_conversation_memory
from services.mia_chat_service_hybrid import detect_language
import re

logger = logging.getLogger(__name__)

class SmartHybridWithMemoryRAGV2:
    """Intelligently routes queries with improved personal interaction handling"""
    
    def __init__(self):
        # Patterns that indicate personal/social interaction (should use enhanced)
        self.personal_patterns = [
            r'\bmy name is\b',
            r'\bi am\b',
            r'\bcall me\b',
            r'\bremember\b',
            r'\bdo you know\b',
            r'\bhow are you\b',
            r'\bnice to meet\b',
            r'\bplease\b.*\b(call|refer|address)\b',
        ]
        
        # Complex query indicators
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
            'personal_request': [
                r'(?:remember|know).*(?:me|my|i)',
                r'(?:call|address|refer).*(?:me|my)',
                r'(?:prefer|like|want).*(?:to be called)',
            ]
        }
        
        # Simple query patterns (use optimized ONLY if truly simple)
        self.simple_patterns = [
            r'^(?:hi|hello|hey)$',  # ONLY simple greeting without additional text
            r'^(?:menu|show menu)$',
            r'^(?:hours|open|closed)\??$',
            r'^(?:phone|number|contact)\??$',
            r'^(?:where|location|address)\??$',
            r'^(?:delivery|takeout|pickup)\??$',
            r'^(?:thank|thanks|bye|goodbye)$',
        ]
        
        # Initialize services
        self.optimized_service = optimized_rag_service
        self.enhanced_service = enhanced_rag_chat_v3
        self.memory = enhanced_conversation_memory
    
    def analyze_complexity_with_memory(self, message: str, client_id: str, restaurant_id: str) -> Dict[str, any]:
        """Analyze query complexity with better personal interaction detection"""
        message_lower = message.lower().strip()
        
        # First, check for personal/social patterns - these ALWAYS need enhanced
        for pattern in self.personal_patterns:
            if re.search(pattern, message_lower):
                return {
                    'is_complex': True,
                    'mode': 'enhanced_v3',
                    'reason': ['personal_interaction'],
                    'confidence': 0.95
                }
        
        # Check conversation memory for context needs
        conversation_history = self.memory.recall(client_id, restaurant_id)
        has_recent_context = len(conversation_history) > 0
        
        # If asking about something ambiguous with history, need enhanced
        if has_recent_context and self.memory.should_clarify_context(client_id, restaurant_id, message):
            return {
                'is_complex': True,
                'mode': 'enhanced_v3',
                'reason': ['needs_conversation_context'],
                'confidence': 0.9
            }
        
        # Check if it's TRULY a simple query (exact match only)
        for pattern in self.simple_patterns:
            if re.search(pattern, message_lower):
                # But if there's recent context about preferences, still use enhanced
                if has_recent_context:
                    recent_preferences = self.memory.extract_preferences(conversation_history)
                    if recent_preferences.get('dietary_restrictions') or recent_preferences.get('favorite_categories'):
                        return {
                            'is_complex': True,
                            'mode': 'enhanced_v3',
                            'reason': ['simple_with_preferences'],
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
        
        # Any greeting with additional content is complex
        if re.search(r'^(?:hi|hello|hey)', message_lower) and len(message.split()) > 3:
            complexity_score += 1
            detected_types.append('greeting_plus')
        
        # Check message length
        if len(message) > 50:
            complexity_score += 1
            detected_types.append('long_query')
        
        # Check for multiple sentences
        if len(re.findall(r'[.!?]', message)) > 1:
            complexity_score += 1
            detected_types.append('multi_sentence')
        
        # Consider conversation history
        if has_recent_context:
            complexity_score += 0.5
            detected_types.append('has_context')
        
        # Higher threshold for using enhanced mode (more conservative)
        if complexity_score >= 2:
            return {
                'is_complex': True,
                'mode': 'enhanced_v3',
                'reason': detected_types,
                'confidence': min(0.9, 0.5 + complexity_score * 0.1)
            }
        
        # Default to optimized only for very simple cases
        return {
            'is_complex': False,
            'mode': 'optimized',
            'reason': 'default',
            'confidence': 0.7
        }
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process request with improved routing"""
        # Analyze query complexity with memory context
        analysis = self.analyze_complexity_with_memory(
            req.message, req.client_id, req.restaurant_id
        )
        
        # Log the routing decision
        logger.info(f"Smart routing V2: {analysis['mode']} (reason: {analysis.get('reason', 'default')})")
        
        # Route to appropriate service with fallback
        if analysis['mode'] == 'enhanced_v3':
            # Try enhanced service first, fall back to optimized if it fails
            try:
                response = self.enhanced_service(req, db)
            except Exception as e:
                logger.error(f"Enhanced service failed: {e}, falling back to optimized")
                response = self.optimized_service(req, db)
        else:
            # Use optimized service
            response = self.optimized_service(req, db)
            
            # Store in conversation memory even for optimized
            response_text = response.answer if hasattr(response, 'answer') else str(response)
            
            # Extract any personal information from the query
            metadata = {'mode': 'optimized', 'complexity': analysis}
            
            # Check if user introduced themselves
            name_match = re.search(r'my name is (\w+)', req.message.lower())
            if name_match:
                metadata['customer_name'] = name_match.group(1).capitalize()
            
            self.memory.remember(
                req.client_id, req.restaurant_id,
                req.message, response_text,
                metadata
            )
        
        # Add routing info
        if hasattr(response, 'metadata'):
            response.metadata = {
                'mode': analysis['mode'], 
                'reason': analysis['reason'],
                'has_memory': True
            }
        
        return response

# Singleton instance
smart_hybrid_memory_rag_v2 = SmartHybridWithMemoryRAGV2()