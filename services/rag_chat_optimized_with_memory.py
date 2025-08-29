"""
Modified optimized RAG service with basic memory functionality
This is a copy of the working optimized service with memory added
"""
import logging
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.mia_chat_service_hybrid import (
    mia_chat_service_hybrid,
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
from services.context_formatter import context_formatter, ContextSection
from schemas.chat import ChatRequest, ChatResponse
import models
import re

logger = logging.getLogger(__name__)

# Simple memory storage
CONVERSATION_MEMORY = {}

class OptimizedRAGChatWithMemory:
    """Optimized RAG with simple memory added"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
    
    def build_minimal_context(self, 
                             db: Session,
                             restaurant_id: str, 
                             query: str, 
                             query_type: QueryType,
                             client_id: str) -> Tuple[str, int]:
        """Build minimal context with memory"""
        
        # Memory key
        memory_key = f"{restaurant_id}:{client_id}"
        
        # Get or create memory
        if memory_key not in CONVERSATION_MEMORY:
            CONVERSATION_MEMORY[memory_key] = {
                'name': None,
                'history': []
            }
        
        memory = CONVERSATION_MEMORY[memory_key]
        
        # Check for name introduction
        name_match = re.search(r'my name is (\w+)', query, re.IGNORECASE)
        if name_match:
            memory['name'] = name_match.group(1).capitalize()
            logger.info(f"Captured name: {memory['name']}")
        
        # For greetings with name, respond personally
        if False and memory['name']:  # was query_type == QueryType.GREETING
            return f"Customer name: {memory['name']}. Use their name in your greeting.", 0
        
        # For name-related queries
        if 'name' in query.lower() and 'my' in query.lower():
            if memory['name']:
                return f"Customer name is {memory['name']}. Acknowledge this appropriately.", 0
            else:
                return "Customer hasn't shared their name yet. Ask politely if needed.", 0
        
        # Original optimized logic continues...
        # Removed GREETING special case - let AI handle naturally

        if False:  # was query_type == QueryType.GREETING

            pass
        if not is_allergen_query:
            try:
                # Search for relevant menu items with increased limit
                relevant_items = self.embedding_service.search_similar_items(
                    db=db,
                    restaurant_id=restaurant_id,
                    query=query,
                    limit=50,  # Get more items
                    threshold=self.similarity_threshold
                )
                
                if relevant_items:
                    # Build context with customer name if known
                    context_parts = []
                    if memory['name']:
                        context_parts.append(f"Customer name: {memory['name']}")
                    
                    context_parts.append("Available menu items:")
                    
                    # Show more items since we have them
                    items_to_show = min(len(relevant_items), 10)
                    for item in relevant_items[:items_to_show]:
                        context_parts.append(f"- {item['name']} (${item['price']})")
                    
                    return "\n".join(context_parts), len(relevant_items)
                    
            except Exception as e:
                logger.warning(f"Embedding search failed: {e}")
        
        # For allergen queries, get comprehensive allergen data
        else:
            allergen_data = allergen_service.get_items_for_restriction(
                db, restaurant_id, query_lower
            )
            
            if allergen_data['safe_items'] or allergen_data['unsafe_items']:
                context_parts = []
                if memory['name']:
                    context_parts.append(f"Customer name: {memory['name']}")
                
                context_parts.append(f"For {allergen_data['restriction_type']}:")
                
                if allergen_data['safe_items']:
                    context_parts.append("\nSAFE items:")
                    for item in allergen_data['safe_items'][:15]:
                        context_parts.append(f"- {item['name']} (${item['price']})")
                
                if allergen_data['unsafe_items']:
                    context_parts.append(f"\nContains {allergen_data['allergen']}:")
                    for item in allergen_data['unsafe_items'][:5]:
                        context_parts.append(f"- {item['name']}")
                
                return "\n".join(context_parts), len(allergen_data['safe_items'])
        
        return "No specific menu items found for this query. Provide helpful general information.", 0
    
    def build_optimized_prompt(self, 
                              restaurant_name: str,
                              query: str,
                              query_type: QueryType,
                              context: str,
                              num_items: int) -> str:
        """Build token-efficient prompt"""
        
        # Ultra-minimal prompt
        # Removed GREETING special case - let AI handle naturally

        if False:  # was query_type == QueryType.GREETING

            pass

    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Main entry point with memory functionality"""
        
        # Handle simple greetings without embeddings
        language = detect_language(req.message)
        query_type = HybridQueryClassifier.classify(req.message)
        
        # Build context with memory
        context, num_items = self.build_minimal_context(
            db, req.restaurant_id, req.message, query_type, req.client_id
        )
        
        # Get restaurant
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="Business not found.")
        
        restaurant_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
        
        # Build prompt
        prompt = self.build_optimized_prompt(
            restaurant_name,
            req.message,
            query_type,
            context,
            num_items
        )
        
        # Get response with minimal tokens
        params = get_hybrid_parameters(query_type)
        params['max_tokens'] = 150  # Strict token limit
        params['temperature'] = 0.3  # More focused responses
        
        answer = get_mia_response_hybrid(prompt, params)
        
        # Store in memory
        memory_key = f"{req.restaurant_id}:{req.client_id}"
        if memory_key in CONVERSATION_MEMORY:
            CONVERSATION_MEMORY[memory_key]['history'].append({
                'q': req.message,
                'a': answer
            })
            # Keep only last 5
            CONVERSATION_MEMORY[memory_key]['history'] = CONVERSATION_MEMORY[memory_key]['history'][-5:]
        
        # Validate but don't over-correct
        validated_answer = response_validator.validate_and_correct(
            answer, db, req.restaurant_id
        )
        
        return ChatResponse(
            answer=validated_answer,
            timestamp=req.message
        )

# Create singleton instance
optimized_rag_with_memory = OptimizedRAGChatWithMemory()