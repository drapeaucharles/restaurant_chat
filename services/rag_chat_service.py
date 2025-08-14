"""
RAG-enhanced chat service that uses vector search for better context
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
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

class RAGEnhancedChat:
    """Chat service enhanced with RAG capabilities"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.3
        self.max_context_items = 5
    
    def build_rag_context(self, 
                         db: Session,
                         restaurant_id: str, 
                         query: str, 
                         query_type: QueryType,
                         menu_items: List[Dict]) -> str:
        """Build context using RAG for better relevance"""
        
        # For greetings, no need for RAG
        if query_type == QueryType.GREETING:
            return ""
        
        # Search for relevant items using embeddings
        relevant_items = self.embedding_service.search_similar_items(
            db=db,
            restaurant_id=restaurant_id,
            query=query,
            limit=self.max_context_items,
            threshold=self.similarity_threshold
        )
        
        if not relevant_items:
            # Fallback to keyword search if no embedding matches
            return self._build_keyword_context(menu_items, query_type, query)
        
        # Build context from relevant items
        context_parts = []
        
        if query_type == QueryType.SPECIFIC_ITEM:
            context_parts.append(f"\nMost relevant menu items for your query:")
            for item in relevant_items:
                line = f"- {item['name']} ({item['price']})"
                if item['description']:
                    line += f": {item['description']}"
                context_parts.append(line)
        
        elif query_type == QueryType.RECOMMENDATION:
            context_parts.append(f"\nBased on your preferences, consider these options:")
            for item in relevant_items:
                line = f"- {item['name']} ({item['price']})"
                if item['description']:
                    line += f": {item['description']}"
                if item['dietary_tags']:
                    line += f" [{', '.join(item['dietary_tags'])}]"
                context_parts.append(line)
        
        elif query_type == QueryType.DIETARY:
            # Filter by dietary requirements mentioned in query
            dietary_items = self._filter_by_dietary(relevant_items, query)
            if dietary_items:
                context_parts.append(f"\nMenu items matching your dietary needs:")
                for item in dietary_items:
                    line = f"- {item['name']} ({item['price']})"
                    if item['dietary_tags']:
                        line += f" [{', '.join(item['dietary_tags'])}]"
                    context_parts.append(line)
            else:
                context_parts.append("\nI'll help you find suitable options based on our menu.")
        
        elif query_type == QueryType.MENU_QUERY:
            # Group by category
            categories = {}
            for item in relevant_items:
                cat = item['category'] or 'main dishes'
                if cat not in categories:
                    categories[cat] = []
                categories[cat].append(item)
            
            context_parts.append("\nOur menu highlights:")
            for cat, items in categories.items():
                context_parts.append(f"\n{cat.title()}:")
                for item in items[:3]:  # Show top 3 per category
                    context_parts.append(f"  - {item['name']} ({item['price']})")
        
        return "\n".join(context_parts)
    
    def _build_keyword_context(self, menu_items: List[Dict], query_type: QueryType, query: str) -> str:
        """Fallback keyword-based context building"""
        # This is similar to the original build_hybrid_context
        # but kept as fallback when embeddings aren't available
        context_parts = []
        query_lower = query.lower()
        
        if query_type == QueryType.SPECIFIC_ITEM:
            relevant_items = []
            
            # Simple keyword matching
            for item in menu_items:
                name = (item.get('dish') or item.get('name', '')).lower()
                desc = item.get('description', '').lower()
                if any(word in name or word in desc for word in query_lower.split()):
                    relevant_items.append(item)
            
            if relevant_items:
                context_parts.append(f"\nRelevant menu items:")
                for item in relevant_items[:self.max_context_items]:
                    name = item.get('dish') or item.get('name', '')
                    price = item.get('price', '')
                    desc = item.get('description', '')
                    line = f"- {name} ({price})"
                    if desc:
                        line += f": {desc}"
                    context_parts.append(line)
        
        return "\n".join(context_parts)
    
    def _filter_by_dietary(self, items: List[Dict], query: str) -> List[Dict]:
        """Filter items by dietary requirements"""
        query_lower = query.lower()
        dietary_keywords = {
            'vegetarian': ['vegetarian'],
            'vegan': ['vegan'],
            'gluten': ['gluten-free'],
            'dairy': ['dairy-free'],
            'nut': ['nut-free']
        }
        
        # Find which dietary requirements are mentioned
        required_tags = []
        for key, tags in dietary_keywords.items():
            if key in query_lower:
                required_tags.extend(tags)
        
        if not required_tags:
            return items
        
        # Filter items that have at least one required tag
        filtered = []
        for item in items:
            item_tags = [tag.lower() for tag in item.get('dietary_tags', [])]
            if any(tag in item_tags for tag in required_tags):
                filtered.append(item)
        
        return filtered

def rag_enhanced_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """RAG-enhanced version of the hybrid chat service"""
    
    logger.info(f"RAG ENHANCED - Restaurant: {req.restaurant_id}, Message: '{req.message}'")
    
    # Skip AI for restaurant staff messages
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Classify query first
    query_type = HybridQueryClassifier.classify(req.message)
    logger.info(f"Query classified as: {query_type.value}")
    
    # Detect language
    language = detect_language(req.message)
    logger.info(f"Detected language: {language}")
    
    # Check if embeddings are available for this restaurant
    embeddings_count = db.execute(text("""
        SELECT COUNT(*) as count 
        FROM menu_embeddings 
        WHERE restaurant_id = :restaurant_id
    """), {'restaurant_id': req.restaurant_id}).scalar()
    
    if embeddings_count == 0:
        logger.info("No embeddings found, falling back to regular hybrid service")
        return mia_chat_service_hybrid(req, db)
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        logger.error(f"Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    try:
        # Get restaurant data
        data = restaurant.data or {}
        restaurant_name = data.get('restaurant_name', req.restaurant_id)
        menu_items = data.get("menu", [])
        
        # Initialize RAG
        rag = RAGEnhancedChat()
        
        # Build Maria's prompt
        system_prompt = get_maria_system_prompt(restaurant_name, query_type, language)
        
        # Build RAG-enhanced context
        context = rag.build_rag_context(db, req.restaurant_id, req.message, query_type, menu_items)
        
        # Add hours if needed
        if query_type == QueryType.HOURS:
            hours = data.get('opening_hours', 'Hours not specified')
            context += f"\n\nOpening hours: {hours}"
        
        # Construct final prompt
        full_prompt = system_prompt
        if context:
            full_prompt += "\n" + context
        full_prompt += f"\n\nCustomer: {req.message}\n{get_persona_name(language)}:"
        
        logger.info(f"RAG-enhanced prompt length: {len(full_prompt)} chars")
        
        # Get parameters
        params = get_hybrid_parameters(query_type)
        
        # Get AI response
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
        
        logger.info(f"RAG-enhanced response generated: {answer[:100]}...")
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in RAG-enhanced service: {e}", exc_info=True)
        # Fallback to regular hybrid service
        return mia_chat_service_hybrid(req, db)

# Import text for the query
from sqlalchemy import text