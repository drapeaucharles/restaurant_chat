"""
Optimized RAG service for MIA decentralized network
Balances accuracy with minimal token usage
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
from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class OptimizedRAGChat:
    """Optimized RAG for cost-effective MIA network usage"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35  # Balanced threshold
        self.max_context_items = 10  # Show more items now that we have 50
    
    def build_minimal_context(self, 
                             db: Session,
                             restaurant_id: str, 
                             query: str, 
                             query_type: QueryType) -> Tuple[str, int]:
        """Build minimal context that prevents hallucination with few tokens"""
        
        # For greetings, no context needed
        if query_type == QueryType.GREETING:
            return "", 0
        
        # Get only the most relevant items via semantic search
        relevant_items = self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=restaurant_id,
            query=query,
            limit=self.max_context_items,
            threshold=self.similarity_threshold
        )
        
        if not relevant_items:
            # Fallback: get a few items by keyword
            keywords = query.lower().split()
            items = db.execute(text("""
                SELECT item_name, item_price, item_category, item_description
                FROM menu_embeddings 
                WHERE restaurant_id = :restaurant_id 
                AND (LOWER(item_name) LIKE ANY(ARRAY[:keywords])
                     OR LOWER(item_category) LIKE ANY(ARRAY[:keywords]))
                LIMIT 5
            """), {
                'restaurant_id': restaurant_id,
                'keywords': [f'%{kw}%' for kw in keywords]
            }).fetchall()
            
            if items:
                # Use validator to create safe context
                relevant_items = [
                    {
                        'name': item.item_name,
                        'price': item.item_price,
                        'category': item.item_category,
                        'description': item.item_description
                    }
                    for item in items
                ]
                return response_validator.create_validated_context(db, restaurant_id, relevant_items), len(items)
            else:
                return "\nPlease check our full menu for available items.", 0
        
        # Use validator to create context with only real items
        validated_context = response_validator.create_validated_context(db, restaurant_id, relevant_items)
        
        # Add total count info
        total_count = db.execute(text("""
            SELECT COUNT(*) FROM menu_embeddings 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id}).scalar()
        
        if total_count > len(relevant_items):
            validated_context += f"\n\n📋 Showing {len(relevant_items)} of {total_count} items. Ask to see more categories or specific types."
        
        return validated_context, len(relevant_items)

def get_optimized_prompt(business_name: str, query_type: QueryType, language: str) -> str:
    """Get minimal but effective system prompt"""
    
    # Ultra-compact personas
    personas = {
        "en": "Maria, friendly assistant",
        "es": "María, asistente amigable", 
        "fr": "Marie, assistante sympathique"
    }
    
    persona = personas.get(language, personas["en"])
    
    # Balanced prompt - helpful but efficient
    prompt = f"You are {persona} at {business_name}.\n"
    prompt += "CRITICAL RULES:\n"
    prompt += "1. ONLY mention items that are listed in the menu context below\n"
    prompt += "2. NEVER invent, guess, or add items not explicitly shown\n"
    prompt += "3. Use exact names and prices from the context\n"
    prompt += "4. If asked about items not in context, say they're not available or ask to see other options\n"
    
    # Query-specific hints
    if query_type == QueryType.SPECIFIC_ITEM:
        prompt += "Show matching items from the context. If none match, politely say it's not available.\n"
    elif query_type == QueryType.DIETARY:
        prompt += "Only recommend items from the context that match dietary needs.\n"
    elif query_type == QueryType.RECOMMENDATION:
        prompt += "Suggest 3-5 items FROM THE CONTEXT with brief reasons.\n"
    elif query_type == QueryType.MENU_QUERY:
        prompt += "Describe ONLY the items shown in the context. Mention if there are more items available.\n"
    
    return prompt

def optimized_rag_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Cost-optimized RAG service for MIA network"""
    
    logger.info(f"OPTIMIZED RAG - Message: '{req.message[:50]}...'")
    
    # Skip AI for restaurant staff
    if req.sender_type == 'restaurant':
        return ChatResponse(answer="")
    
    # Quick classification
    query_type = HybridQueryClassifier.classify(req.message)
    
    # For simple greetings, use cached response
    if query_type == QueryType.GREETING:
        language = detect_language(req.message)
        greetings = {
            "en": "Hello! Welcome to our restaurant. How can I help you today?",
            "es": "¡Hola! Bienvenido a nuestro restaurante. ¿Cómo puedo ayudarte?",
            "fr": "Bonjour! Bienvenue dans notre restaurant. Comment puis-je vous aider?"
        }
        return ChatResponse(answer=greetings.get(language, greetings["en"]))
    
    # Check embeddings availability
    try:
        has_embeddings = db.execute(text("""
            SELECT EXISTS(
                SELECT 1 FROM menu_embeddings 
                WHERE restaurant_id = :restaurant_id 
                LIMIT 1
            )
        """), {'restaurant_id': req.restaurant_id}).scalar()
        
        if not has_embeddings:
            # Fallback to basic service
            return mia_chat_service_hybrid(req, db)
    except:
        return mia_chat_service_hybrid(req, db)
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        return ChatResponse(answer="Business not found.")
    
    try:
        # Get business info
        data = restaurant.data or {}
        business_name = data.get('restaurant_name', 'our restaurant')
        language = detect_language(req.message)
        
        # Initialize optimized RAG
        rag = OptimizedRAGChat()
        
        # Get minimal prompt
        system_prompt = get_optimized_prompt(business_name, query_type, language)
        
        # Build minimal context
        context, item_count = rag.build_minimal_context(db, req.restaurant_id, req.message, query_type)
        
        # Construct final prompt (very compact)
        full_prompt = system_prompt + context
        full_prompt += f"\nUser: {req.message}\nReply:"
        
        # Log token estimate (rough: 1 token ≈ 4 chars)
        token_estimate = len(full_prompt) // 4
        logger.info(f"Prompt tokens (est): {token_estimate}, Items: {item_count}")
        
        # Dynamic response length based on query
        length_config = ResponseLengthManager.determine_length(req.message, query_type.value)
        response_instruction = ResponseLengthManager.format_response_instruction(length_config)
        
        # Add response length instruction to prompt
        full_prompt += f"\n{response_instruction}"
        
        # Set parameters based on length config
        params = {
            "temperature": 0.5,  # Balanced creativity
            "max_tokens": length_config["max_tokens"]
        }
        
        # Log what we're doing
        logger.info(f"Response length: {length_config['length'].value}, max_tokens: {length_config['max_tokens']}")
        
        # Get response from MIA network
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Validate response to catch any hallucinations
        validation_result = response_validator.validate_response(db, req.restaurant_id, answer)
        
        if not validation_result['valid']:
            logger.warning(f"Hallucinated items detected: {validation_result['hallucinated_items']}")
            
            # If hallucination detected, retry with stricter prompt
            strict_prompt = full_prompt.replace("User:", "REMINDER: Only mention items from the context above!\n\nUser:")
            answer = get_mia_response_hybrid(strict_prompt, params)
            
            # Validate again
            second_validation = response_validator.validate_response(db, req.restaurant_id, answer)
            if not second_validation['valid']:
                logger.error(f"Persistent hallucination after retry: {second_validation['hallucinated_items']}")
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Optimized RAG error: {e}")
        return mia_chat_service_hybrid(req, db)

# Export
optimized_rag_service = optimized_rag_chat_service