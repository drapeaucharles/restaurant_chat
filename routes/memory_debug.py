"""
Debug endpoint to see what memory is stored and what context is built
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.conversation_memory_enhanced_lazy import enhanced_conversation_memory
from services.rag_chat_enhanced_v3_lazy import EnhancedRAGChatV3
from services.mia_chat_service_hybrid import HybridQueryClassifier
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/memory-debug/{restaurant_id}/{client_id}")
async def debug_memory(restaurant_id: str, client_id: str, db: Session = Depends(get_db)):
    """Debug what's in memory and what context would be built"""
    
    # Get stored memory
    memory_info = enhanced_conversation_memory.extract_customer_info(restaurant_id, client_id)
    history = enhanced_conversation_memory.get_history(restaurant_id, client_id)
    
    # Build context like the service would
    rag = EnhancedRAGChatV3()
    test_query = "Hello"
    query_type = HybridQueryClassifier.classify(test_query)
    
    context_sections = rag.build_context_with_memory(
        db, restaurant_id, client_id, test_query, query_type
    )
    
    # Format context sections for display
    formatted_context = {}
    for section, content in context_sections.items():
        formatted_context[section.value] = content
    
    return {
        "stored_memory": {
            "customer_info": memory_info,
            "history_count": len(history),
            "last_interactions": [
                {
                    "query": turn.query,
                    "response": turn.response[:100] + "...",
                    "timestamp": turn.timestamp
                }
                for turn in history[-3:]
            ] if history else []
        },
        "context_built": formatted_context,
        "would_personalization_be_included": bool(formatted_context.get('personalization'))
    }