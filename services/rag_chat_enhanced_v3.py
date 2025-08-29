"""
Enhanced RAG service V3 with improved conversation memory
"""
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.mia_chat_service_hybrid import (
    HybridQueryClassifier,
    QueryType,
    get_hybrid_parameters,
    get_mia_response_hybrid,
    detect_language,
    get_persona_name
)
from services.embedding_service import embedding_service
from services.response_length_manager import ResponseLengthManager
from services.response_validator import response_validator
from services.allergen_service import allergen_service
from services.context_enrichment import context_enrichment
from services.confidence_scorer import confidence_scorer
from services.semantic_cache import semantic_cache
from services.conversation_memory_enhanced_fixed import enhanced_conversation_memory
from services.context_formatter import context_formatter, ContextSection
from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class EnhancedRAGChatV3:
    """Enhanced RAG with improved conversation memory and context awareness"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
        self.response_length_manager = ResponseLengthManager()
        
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Main chat entry point with enhanced conversation awareness"""
        try:
            # Check if we need clarification based on conversation history
            if enhanced_conversation_memory.should_clarify_context(
                req.client_id, req.restaurant_id, req.message
            ):
                # Get last mentioned items for context
                last_items = enhanced_conversation_memory.get_last_mentioned_items(
                    req.client_id, req.restaurant_id
                )
                if not last_items:
                    clarification = "I'd be happy to help! Could you please clarify what you're referring to?"
                    # Store this interaction
                    enhanced_conversation_memory.remember(
                        req.client_id, req.restaurant_id,
                        req.message, clarification,
                        {'needs_clarification': True}
                    )
                    return ChatResponse(answer=clarification, timestamp=req.message)
            
            # Check semantic cache first
            cache_hit = semantic_cache.find_similar_response(req.restaurant_id, req.message)
            if cache_hit and cache_hit['similarity'] > 0.9:  # Higher threshold for cache
                logger.info(f"Semantic cache hit with {cache_hit['similarity']:.2f} similarity")
                # Still store in conversation memory
                enhanced_conversation_memory.remember(
                    req.client_id, req.restaurant_id,
                    req.message, cache_hit['response'],
                    {'from_cache': True, 'similarity': cache_hit['similarity']}
                )
                return ChatResponse(
                    answer=cache_hit['response'],
                    timestamp=req.message
                )
            
            # Get restaurant data
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                return ChatResponse(
                    answer="Restaurant not found.",
                    timestamp=req.message
                )
            
            # Detect language and classify query
            language = detect_language(req.message)
            query_type = HybridQueryClassifier.classify(req.message)
            
            # Get full conversation context
            conversation_context = enhanced_conversation_memory.get_conversation_context(
                req.client_id, req.restaurant_id
            )
            
            # Get preferences summary
            preferences_summary = enhanced_conversation_memory.get_context_summary(
                req.client_id, req.restaurant_id
            )
            
            # Build context sections with enhanced memory
            context_sections = self._build_context_sections(
                db, req, restaurant, query_type, 
                conversation_context, preferences_summary
            )
            
            # Score confidence with conversation awareness
            matched_items = self._get_matched_items(db, req.restaurant_id, req.message)
            
            # Extract mentioned items for metadata
            mentioned_items = self._extract_mentioned_items(matched_items)
            
            confidence = confidence_scorer.score_menu_match(req.message, matched_items)
            
            # Build prompt with enhanced context
            prompt = self._build_enhanced_prompt(
                restaurant_name=restaurant.data.get('name', 'our restaurant'),
                query=req.message,
                query_type=query_type,
                language=language,
                context_sections=context_sections,
                confidence=confidence,
                has_conversation_history=bool(conversation_context)
            )
            
            # Adjust parameters based on confidence and conversation state
            params = get_hybrid_parameters(query_type)
            params['temperature'] = self._get_adaptive_temperature(
                query_type, confidence, bool(conversation_context)
            )
            
            # Get response from MIA
            answer = get_mia_response_hybrid(prompt, params)
            
            # Validate and improve response
            validated_answer = response_validator.validate_and_correct(
                answer, db, req.restaurant_id
            )
            
            # Extract any allergen information mentioned
            allergen_info = self._extract_allergen_mentions(req.message, validated_answer)
            
            # Store in enhanced conversation memory with metadata
            enhanced_conversation_memory.remember(
                req.client_id, req.restaurant_id,
                req.message, validated_answer,
                {
                    'query_type': query_type.value,
                    'confidence': confidence,
                    'language': language,
                    'mentioned_items': mentioned_items,
                    'allergens': allergen_info
                }
            )
            
            # Store in semantic cache
            semantic_cache.store_response(
                req.restaurant_id, 
                req.message, 
                validated_answer,
                {'query_type': query_type.value, 'confidence': confidence}
            )
            
            return ChatResponse(
                answer=validated_answer,
                timestamp=req.message
            )
            
        except Exception as e:
            logger.error(f"Enhanced RAG V3 error: {e}")
            return ChatResponse(
                answer="I apologize, but I'm having trouble processing your request. Please try again.",
                timestamp=req.message
            )
    
    def _build_context_sections(self, db: Session, req: ChatRequest,
                               restaurant: models.Restaurant, 
                               query_type: QueryType,
                               conversation_context: str,
                               preferences_summary: str) -> Dict[ContextSection, str]:
        """Build organized context sections with conversation history"""
        sections = {}
        
        # Get relevant menu items
        relevant_items = self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=req.restaurant_id,
            query=req.message,
            limit=self.max_context_items,
            threshold=self.similarity_threshold
        )
        
        # Menu items section
        if relevant_items and True  # was query_type != QueryType.GREETING:
            show_descriptions = query_type in [QueryType.RECOMMENDATION, QueryType.SPECIFIC_ITEM]
            sections[ContextSection.MENU_ITEMS] = context_formatter.format_menu_items(
                relevant_items, show_descriptions
            )
        
        # Restaurant info section (for greetings or general queries)
        # Removed GREETING special case - let AI handle naturally

        if False:  # was query_type == QueryType.GREETING

            pass
            if restaurant.data.get('name'):
                restaurant_info.append(f"Name: {restaurant.data['name']}")
            if restaurant.data.get('story'):
                restaurant_info.append(f"About: {restaurant.data['story'][:100]}...")
            if restaurant_info:
                sections[ContextSection.RESTAURANT_INFO] = "\n".join(restaurant_info)
        
        # Dietary section for allergen queries
        if any(word in req.message.lower() for word in ['allerg', 'dietary', 'vegan', 'vegetarian', 'gluten']):
            dietary_info = self._get_dietary_context(db, req.restaurant_id, req.message)
            if dietary_info:
                sections[ContextSection.DIETARY_INFO] = dietary_info
        
        # Add conversation history if available
        if conversation_context:
            sections[ContextSection.CONVERSATION_HISTORY] = conversation_context
        
        # Add preferences summary if available
        if preferences_summary:
            sections[ContextSection.PREFERENCES] = preferences_summary
        
        # Instructions section with conversation awareness
        instructions = self._create_conversation_aware_instructions(
            query_type, 
            len(relevant_items),
            bool(conversation_context),
            bool(preferences_summary)
        )
        sections[ContextSection.INSTRUCTIONS] = instructions
        
        return sections
    
    def _build_enhanced_prompt(self, restaurant_name: str, query: str,
                              query_type: QueryType, language: str,
                              context_sections: Dict[ContextSection, str],
                              confidence: float,
                              has_conversation_history: bool) -> str:
        """Build prompt with enhanced conversation awareness"""
        persona_name = get_persona_name(language)
        
        # System prompt with conversation awareness
        system_prompt = f"""You are {persona_name}, a friendly and knowledgeable AI assistant for {restaurant_name}.

Key traits:
• Warm and welcoming personality
• Excellent memory - remember previous interactions
• Natural conversation style that builds on context
• Language: {language} (match the customer's language naturally)
"""

        if has_conversation_history:
            system_prompt += "\n• You have been chatting with this customer - maintain continuity"
        
        # Add confidence-based guidance
        if confidence < 0.5:
            system_prompt += "\n• The query might be ambiguous - consider asking for clarification"
        elif confidence > 0.8:
            system_prompt += "\n• You have strong menu matches - be specific and confident"
        
        # Format context
        formatted_context = context_formatter.format_context(context_sections)
        
        # Build the complete prompt
        full_prompt = f"""{system_prompt}

{formatted_context}

Customer Query: {query}

Your Response:"""
        
        return full_prompt
    
    def _create_conversation_aware_instructions(self, query_type: QueryType, 
                                               num_items: int,
                                               has_history: bool,
                                               has_preferences: bool) -> str:
        """Create instructions that consider conversation state"""
        base_instructions = context_formatter.create_clear_instructions(
            query_type.value,
            self._get_query_constraints(query_type, num_items)
        )
        
        additional_instructions = []
        
        if has_history:
            additional_instructions.append(
                "• Reference previous conversation naturally when relevant"
            )
        
        if has_preferences:
            additional_instructions.append(
                "• Consider the customer's known preferences and dietary restrictions"
            )
        
        if query_type == QueryType.FOLLOW_UP:
            additional_instructions.append(
                "• This appears to be a follow-up question - maintain context"
            )
        
        if additional_instructions:
            return base_instructions + "\n\n" + "\n".join(additional_instructions)
        
        return base_instructions
    
    def _get_adaptive_temperature(self, query_type: QueryType, 
                                 confidence: float, 
                                 has_context: bool) -> float:
        """Get temperature based on multiple factors"""
        base_temp = confidence_scorer.adaptive_temperature(query_type.value, confidence)
        
        # Lower temperature if we have conversation context (more consistent)
        if has_context:
            base_temp *= 0.9
        
        # Ensure reasonable bounds
        return max(0.1, min(0.9, base_temp))
    
    def _extract_mentioned_items(self, matched_items: List[Dict]) -> List[str]:
        """Extract menu item names from matches"""
        return [item.get('name', '') for item in matched_items[:5] if item.get('name')]
    
    def _extract_allergen_mentions(self, query: str, response: str) -> List[str]:
        """Extract any allergen mentions from query and response"""
        allergens = []
        common_allergens = [
            'nuts', 'peanuts', 'dairy', 'milk', 'eggs', 'shellfish', 
            'fish', 'soy', 'wheat', 'gluten', 'sesame'
        ]
        
        combined_text = (query + " " + response).lower()
        
        for allergen in common_allergens:
            if allergen in combined_text:
                allergens.append(allergen)
        
        return allergens
    
    def _get_matched_items(self, db: Session, restaurant_id: str, query: str) -> List[Dict]:
        """Get menu items that match the query"""
        return self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=restaurant_id,
            query=query,
            limit=5,
            threshold=self.similarity_threshold
        )
    
    def _get_dietary_context(self, db: Session, restaurant_id: str, query: str) -> str:
        """Get dietary information context"""
        # Implementation would fetch dietary info from allergen service
        return allergen_service.get_dietary_info_context(db, restaurant_id, query)
    
    def _get_query_constraints(self, query_type: QueryType, num_items: int) -> Dict:
        """Get constraints based on query type"""
        constraints = {
            'response_style': 'conversational',
            'include_prices': query_type == QueryType.PRICE_INQUIRY,
            'include_descriptions': query_type in [QueryType.RECOMMENDATION, QueryType.SPECIFIC_ITEM],
            'max_items': min(num_items, 5) if query_type == QueryType.MENU_EXPLORATION else 3
        }
        return constraints

# Create singleton instance
enhanced_rag_chat_v3 = EnhancedRAGChatV3()