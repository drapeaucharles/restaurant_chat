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
from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class OptimizedRAGChat:
    """Optimized RAG for cost-effective MIA network usage"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35  # Balanced threshold
        self.max_context_items = 7  # Show more items, but not all
    
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
                SELECT item_name, item_price, item_category 
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
                context = "\nAvailable items:\n"
                for item in items:
                    context += f"• {item.item_name} ({item.item_price})\n"
                return context, len(items)
            else:
                return "\nPlease check our full menu for available items.", 0
        
        # Build context with more items
        context = "\nRelevant items:\n"
        for i, item in enumerate(relevant_items):
            context += f"• {item['name']} ({item['price']})"
            if query_type == QueryType.DIETARY and item.get('dietary_tags'):
                context += f" [{', '.join(item['dietary_tags'])}]"
            elif i < 3:  # Add brief description for top 3
                desc = item.get('description', '')
                if desc and len(desc) > 50:
                    desc = desc[:50] + "..."
                if desc:
                    context += f" - {desc}"
            context += "\n"
        
        # Check if there might be more items
        total_count = db.execute(text("""
            SELECT COUNT(*) FROM menu_embeddings 
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id}).scalar()
        
        if total_count > len(relevant_items):
            context += f"\n📋 Showing {len(relevant_items)} of {total_count} items. Ask to see more categories or specific types."
        
        # Smarter instruction
        context += "\n💡 Focus on these items. Mention if customer wants to see other options."
        
        return context, len(relevant_items)

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
    prompt += "Rules: Be helpful and complete. List items with prices. If showing partial results, mention more options are available.\n"
    
    # Query-specific hints
    if query_type == QueryType.SPECIFIC_ITEM:
        prompt += "Show all matching items. If there are many, show the best ones and mention there are more.\n"
    elif query_type == QueryType.DIETARY:
        prompt += "Focus on dietary requirements. Be thorough but concise.\n"
    elif query_type == QueryType.RECOMMENDATION:
        prompt += "Suggest 3-5 items with brief reasons why.\n"
    elif query_type == QueryType.MENU_QUERY:
        prompt += "Give an overview of categories and highlight popular items.\n"
    
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
        
        # Balanced parameters for MIA
        params = {
            "temperature": 0.5,  # Balanced creativity
            "max_tokens": 250    # Reasonable response length
        }
        
        # Adjust for different query types
        if query_type == QueryType.MENU_QUERY:
            params["max_tokens"] = 350  # More space for menu overview
        elif query_type == QueryType.GREETING:
            params["max_tokens"] = 100  # Keep greetings short
        
        # Get response from MIA network
        answer = get_mia_response_hybrid(full_prompt, params)
        
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