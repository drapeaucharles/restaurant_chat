"""
Improved RAG chat service that prevents hallucination efficiently
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from services.mia_chat_service_hybrid import (
    mia_chat_service_hybrid,
    HybridQueryClassifier,
    QueryType,
    get_maria_system_prompt,
    get_hybrid_parameters,
    get_mia_response_hybrid,
    detect_language,
    get_persona_name
)
from services.embedding_service import embedding_service
from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class ImprovedRAGChat:
    """Improved RAG that prevents hallucination efficiently"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.3
        self.max_context_items = 5
    
    def build_improved_context(self, 
                              db: Session,
                              restaurant_id: str, 
                              query: str, 
                              query_type: QueryType) -> str:
        """Build context that prevents hallucination without being overly strict"""
        
        # For greetings, no context needed
        if query_type == QueryType.GREETING:
            return ""
        
        # Get ALL available items from database (ground truth)
        all_items = db.execute(text("""
            SELECT item_name, item_price, item_category, item_description, dietary_tags
            FROM menu_embeddings 
            WHERE restaurant_id = :restaurant_id 
            ORDER BY item_category, item_name
        """), {'restaurant_id': restaurant_id}).fetchall()
        
        if not all_items:
            return "\nNo menu items available in database."
        
        # Search for semantically relevant items
        relevant_items = self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=restaurant_id,
            query=query,
            limit=self.max_context_items,
            threshold=self.similarity_threshold
        )
        
        # Build context with two parts: relevant items + complete list
        context_parts = []
        
        # Part 1: Relevant items based on query
        if relevant_items:
            context_parts.append("\n📍 Most relevant to your query:")
            for item in relevant_items:
                context_parts.append(f"• {item['name']} ({item['price']}) - {item['description']}")
        
        # Part 2: Complete inventory (prevents hallucination)
        context_parts.append("\n📋 Complete menu available:")
        current_category = None
        
        for item in all_items:
            if item.item_category != current_category:
                current_category = item.item_category or "Specials"
                context_parts.append(f"\n{current_category}:")
            
            line = f"• {item.item_name} ({item.item_price})"
            if item.dietary_tags:
                tags = item.dietary_tags if isinstance(item.dietary_tags, list) else []
                if tags:
                    line += f" [{', '.join(tags)}]"
            context_parts.append(line)
        
        # Add universal instruction
        context_parts.append("\n⚠️ Only mention items from the list above. Prices are in USD ($).")
        
        return "\n".join(context_parts)

def improved_rag_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Improved RAG service that prevents hallucination efficiently"""
    
    logger.info(f"IMPROVED RAG - Restaurant: {req.restaurant_id}, Message: '{req.message}'")
    
    # Skip AI for restaurant staff
    if req.sender_type == 'restaurant':
        return ChatResponse(answer="")
    
    # Classify query
    query_type = HybridQueryClassifier.classify(req.message)
    language = detect_language(req.message)
    
    # Check if embeddings exist
    try:
        count = db.execute(text("""
            SELECT COUNT(*) FROM menu_embeddings 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': req.restaurant_id}).scalar()
        
        if count == 0:
            logger.info("No embeddings, falling back to hybrid service")
            return mia_chat_service_hybrid(req, db)
    except:
        logger.info("Embeddings table issue, falling back to hybrid service")
        return mia_chat_service_hybrid(req, db)
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        return ChatResponse(answer="I cannot find information about this business.")
    
    try:
        # Get business data
        data = restaurant.data or {}
        business_name = data.get('restaurant_name', req.restaurant_id)
        
        # Initialize improved RAG
        rag = ImprovedRAGChat()
        
        # Get base prompt
        system_prompt = get_maria_system_prompt(business_name, query_type, language)
        
        # Build improved context
        context = rag.build_improved_context(db, req.restaurant_id, req.message, query_type)
        
        # Construct final prompt
        full_prompt = system_prompt + context
        full_prompt += f"\n\nCustomer: {req.message}\n{get_persona_name(language)}:"
        
        # Get parameters (lower temperature for accuracy)
        params = get_hybrid_parameters(query_type)
        params["temperature"] = min(params.get("temperature", 0.7), 0.5)
        
        # Get AI response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Quick validation - no euros!
        if "€" in answer:
            answer = answer.replace("€", "$")
        
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
        logger.error(f"Error in improved RAG: {e}", exc_info=True)
        return mia_chat_service_hybrid(req, db)

# Export the service
rag_improved_service = improved_rag_chat_service