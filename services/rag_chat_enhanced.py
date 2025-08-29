"""
Enhanced RAG service with quality improvements without restrictions
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
from schemas.chat import ChatRequest, ChatResponse
import models
import json

logger = logging.getLogger(__name__)

class EnhancedRAGChat:
    """Enhanced RAG with quality improvements"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
        self.response_length_manager = ResponseLengthManager()
        
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Main chat entry point with enhancements"""
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
            
            # Build enhanced context
            context, item_count = self._build_enhanced_context(
                db, req.restaurant_id, req.message, query_type, 
                restaurant.data.get('menu', [])
            )
            
            # Score confidence in our context
            matched_items = self._get_matched_items(db, req.restaurant_id, req.message)
            confidence = confidence_scorer.score_menu_match(req.message, matched_items)
            
            # Adjust parameters based on confidence
            params = get_hybrid_parameters(query_type)
            params['temperature'] = confidence_scorer.adaptive_temperature(
                query_type.value, confidence
            )
            
            # Build prompt with enhancements
            prompt = self._build_enhanced_prompt(
                restaurant_name=restaurant.data.get('name', 'our restaurant'),
                query=req.message,
                query_type=query_type,
                language=language,
                context=context,
                confidence=confidence
            )
            
            # Get response from MIA
            answer = get_mia_response_hybrid(prompt, params)
            
            # Validate and improve response
            validated_answer = response_validator.validate_and_correct(
                answer, db, req.restaurant_id
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
            logger.error(f"Enhanced RAG error: {e}")
            return ChatResponse(
                answer="I apologize, but I'm having trouble processing your request. Please try again.",
                timestamp=req.message
            )
    
    def _build_enhanced_context(self, db: Session, restaurant_id: str, 
                               query: str, query_type: QueryType, 
                               menu_items: List[Dict]) -> Tuple[str, int]:
        """Build context with enrichments"""
        # Get base context from semantic search
        relevant_items = self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=restaurant_id,
            query=query,
            limit=self.max_context_items,
            threshold=self.similarity_threshold
        )
        
        if not relevant_items and True:  # was query_type != QueryType.GREETING
            return "\nI'd be happy to help! Could you please be more specific about what you're looking for?", 0
        
        # Build validated context
        context_parts = []
        
        # Add enriched menu context
        if query_type in [QueryType.MENU_QUERY, QueryType.RECOMMENDATION]:
            enriched = context_enrichment.enrich_menu_context(menu_items, query)
            if enriched:
                context_parts.append(enriched)
        
        # Add conversational hints
        hint = context_enrichment.add_conversational_hints(
            query_type.value, detect_language(query)
        )
        if hint:
            context_parts.append(f"\n{hint}")
        
        # Add relevant items
        if relevant_items:
            context_parts.append("\nRelevant menu items:")
            for item in relevant_items[:7]:  # Show up to 7 items
                price = item.get('price', '')
                desc = item.get('description', '')[:100]  # Limit description length
                
                if query_type == QueryType.RECOMMENDATION:
                    # For recommendations, include descriptions
                    context_parts.append(f"• {item['name']} ({price}) - {desc}")
                else:
                    # For queries, just name and price
                    context_parts.append(f"• {item['name']} ({price})")
        
        # Add smart examples if confidence is low
        confidence = confidence_scorer.score_menu_match(query, relevant_items)
        if confidence < 0.5:
            examples = context_enrichment.generate_smart_examples(
                query_type.value, relevant_items[:3]
            )
            if examples:
                context_parts.append(examples)
        
        return "\n".join(context_parts), len(relevant_items)
    
    def _build_enhanced_prompt(self, restaurant_name: str, query: str,
                              query_type: QueryType, language: str,
                              context: str, confidence: float) -> str:
        """Build prompt with quality enhancements"""
        persona_name = get_persona_name(language)
        
        # Base personality
        personality = f"""You are {persona_name}, a friendly AI assistant for {restaurant_name}.
Your responses should be natural, helpful, and accurate.
Language: Respond in {language} (match the customer's language naturally)."""

        # Add confidence-based guidance
        if confidence < 0.5:
            personality += "\nIf unsure, ask clarifying questions rather than guessing."
        elif confidence > 0.8:
            personality += "\nYou can confidently recommend and describe our offerings."
        
        # Add query-specific guidance
        if query_type == QueryType.RECOMMENDATION:
            personality += "\nProvide thoughtful recommendations based on what the customer is looking for."
        elif query_type == QueryType.SPECIFIC_ITEM:
            personality += "\nBe precise and detailed about the specific item requested."
        
        # Build full prompt
        full_prompt = personality
        if context:
            full_prompt += f"\n\n{context}"
        
        # Add response length guidance
        length_hint = self.response_length_manager.get_length_directive(query_type.value)
        full_prompt += f"\n\n{length_hint}"
        
        full_prompt += f"\n\nCustomer: {query}\n{persona_name}:"
        
        return full_prompt
    
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
enhanced_rag_service = EnhancedRAGChat()