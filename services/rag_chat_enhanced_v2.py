"""
Enhanced RAG service V2 with clear context separation
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
from services.conversation_memory import conversation_memory
from services.context_formatter import context_formatter, ContextSection
from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class EnhancedRAGChatV2:
    """Enhanced RAG with clear context separation"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
        self.response_length_manager = ResponseLengthManager()
        
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Main chat entry point with clear context formatting"""
        try:
            # Check semantic cache first
            cache_hit = semantic_cache.find_similar_response(req.restaurant_id, req.message)
            if cache_hit:
                logger.info(f"Semantic cache hit with {cache_hit['similarity']:.2f} similarity")
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
            
            # Get conversation memory
            memory_context = conversation_memory.get_context_summary(
                req.client_id, req.restaurant_id
            )
            
            # Build context sections
            context_sections = self._build_context_sections(
                db, req, restaurant, query_type, memory_context
            )
            
            # Score confidence
            matched_items = self._get_matched_items(db, req.restaurant_id, req.message)
            confidence = confidence_scorer.score_menu_match(req.message, matched_items)
            
            # Build prompt with clear formatting
            prompt = self._build_clear_prompt(
                restaurant_name=restaurant.data.get('name', 'our restaurant'),
                query=req.message,
                query_type=query_type,
                language=language,
                context_sections=context_sections,
                confidence=confidence
            )
            
            # Adjust parameters based on confidence
            params = get_hybrid_parameters(query_type)
            params['temperature'] = confidence_scorer.adaptive_temperature(
                query_type.value, confidence
            )
            
            # Get response from MIA
            answer = get_mia_response_hybrid(prompt, params)
            
            # Validate and improve response
            validated_answer = response_validator.validate_and_correct(
                answer, db, req.restaurant_id
            )
            
            # Store in conversation memory
            conversation_memory.remember(
                req.client_id, req.restaurant_id,
                req.message, validated_answer,
                {'query_type': query_type.value, 'confidence': confidence}
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
            logger.error(f"Enhanced RAG V2 error: {e}")
            return ChatResponse(
                answer="I apologize, but I'm having trouble processing your request. Please try again.",
                timestamp=req.message
            )
    
    def _build_context_sections(self, db: Session, req: ChatRequest,
                               restaurant: models.Restaurant, 
                               query_type: QueryType,
                               memory_context: str) -> Dict[ContextSection, str]:
        """Build organized context sections"""
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
        if relevant_items:
            show_descriptions = query_type in [QueryType.RECOMMENDATION, QueryType.SPECIFIC_ITEM]
            sections[ContextSection.MENU_ITEMS] = context_formatter.format_menu_items(
                relevant_items, show_descriptions
            )
        
        # Restaurant info section - removed greeting special case
        if False:  # query_type == QueryType.GREETING - removed
            restaurant_info = []
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
        
        # Conversation history if available
        if memory_context:
            sections[ContextSection.PREFERENCES] = memory_context
        
        # Instructions section
        instructions = context_formatter.create_clear_instructions(
            query_type.value,
            self._get_query_constraints(query_type, len(relevant_items))
        )
        sections[ContextSection.INSTRUCTIONS] = instructions
        
        return sections
    
    def _build_clear_prompt(self, restaurant_name: str, query: str,
                           query_type: QueryType, language: str,
                           context_sections: Dict[ContextSection, str],
                           confidence: float) -> str:
        """Build prompt with clear context separation"""
        persona_name = get_persona_name(language)
        
        # System prompt (personality)
        system_prompt = f"""You are {persona_name}, a friendly and knowledgeable AI assistant for {restaurant_name}.

Key traits:
• Warm and welcoming personality
• Accurate and helpful responses
• Natural conversation style
• Language: {language} (match the customer's language naturally)"""

        # Add confidence-based adjustments
        if confidence < 0.5:
            system_prompt += "\n• When uncertain, ask clarifying questions"
        elif confidence > 0.8:
            system_prompt += "\n• Confidently share details about our offerings"
        
        # Use formatter to create clear prompt
        return context_formatter.format_prompt_with_context(
            system_prompt=system_prompt,
            context_sections=context_sections,
            customer_message=query,
            assistant_name=persona_name
        )
    
    def _get_dietary_context(self, db: Session, restaurant_id: str, query: str) -> str:
        """Get dietary-specific context"""
        dietary_items = {}
        
        query_lower = query.lower()
        if 'nut' in query_lower:
            dietary_items['nut-free'] = allergen_service.get_items_for_dietary_need(
                db, restaurant_id, 'nut-free'
            )[:5]
        if 'dairy' in query_lower or 'lactose' in query_lower:
            dietary_items['dairy-free'] = allergen_service.get_items_for_dietary_need(
                db, restaurant_id, 'dairy-free'
            )[:5]
        if 'gluten' in query_lower:
            dietary_items['gluten-free'] = allergen_service.get_items_for_dietary_need(
                db, restaurant_id, 'gluten-free'
            )[:5]
        if 'vegetarian' in query_lower:
            dietary_items['vegetarian'] = allergen_service.get_items_for_dietary_need(
                db, restaurant_id, 'vegetarian'
            )[:5]
        if 'vegan' in query_lower:
            dietary_items['vegan'] = allergen_service.get_items_for_dietary_need(
                db, restaurant_id, 'vegan'
            )[:5]
        
        return context_formatter.format_dietary_info(dietary_items)
    
    def _get_query_constraints(self, query_type: QueryType, item_count: int) -> List[str]:
        """Get specific constraints based on query type"""
        constraints = []
        
        if query_type == QueryType.SPECIFIC_ITEM and item_count == 0:
            constraints.append("The requested item is not available - suggest alternatives from the context")
        elif query_type == QueryType.MENU_QUERY and item_count < 3:
            constraints.append("Mention that these are some of our options, not the complete menu")
        elif query_type == QueryType.RECOMMENDATION:
            constraints.append("Provide 2-3 recommendations with brief explanations")
        
        return constraints
    
    def _get_matched_items(self, db: Session, restaurant_id: str, query: str) -> List[Dict]:
        """Get items that match the query for confidence scoring"""
        items = self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=restaurant_id,
            query=query,
            limit=10,
            threshold=0.3
        )
        return items

# Create singleton instance
enhanced_rag_service_v2 = EnhancedRAGChatV2()