"""
Dynamic chat endpoint that uses restaurant-specific RAG mode
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from datetime import datetime
from services.mia_chat_service_hybrid import mia_chat_service_hybrid, get_or_create_client
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Import all available services
chat_services = {}

# Load optimized service
try:
    from services.rag_chat_optimized import optimized_rag_service
    chat_services['optimized'] = optimized_rag_service
    logger.info("Loaded optimized RAG service")
except ImportError:
    logger.warning("Optimized RAG service not available")

# Load enhanced v2 service
try:
    from services.rag_chat_enhanced_v2 import enhanced_rag_service_v2
    chat_services['enhanced_v2'] = enhanced_rag_service_v2
    logger.info("Loaded enhanced v2 RAG service")
except ImportError:
    logger.warning("Enhanced v2 RAG service not available")

# Load enhanced v3 service
try:
    from services.rag_chat_enhanced_v3 import enhanced_rag_chat_v3
    chat_services['enhanced_v3'] = enhanced_rag_chat_v3
    logger.info("Loaded enhanced v3 RAG service")
except ImportError:
    logger.warning("Enhanced v3 RAG service not available")

# Load hybrid smart service
try:
    from services.rag_chat_hybrid_smart import smart_hybrid_rag
    chat_services['hybrid_smart'] = smart_hybrid_rag
    logger.info("Loaded hybrid smart RAG service")
except ImportError:
    logger.warning("Hybrid smart RAG service not available")

# Load hybrid smart with memory service
try:
    from services.rag_chat_hybrid_smart_memory import smart_hybrid_memory_rag
    chat_services['hybrid_smart_memory'] = smart_hybrid_memory_rag
    logger.info("Loaded hybrid smart with memory RAG service")
except ImportError:
    logger.warning("Hybrid smart with memory RAG service not available")

# Load hybrid smart with memory V2 service (improved personal handling)
try:
    from services.rag_chat_hybrid_smart_memory_v2 import smart_hybrid_memory_rag_v2
    chat_services['hybrid_smart_memory_v2'] = smart_hybrid_memory_rag_v2
    logger.info("Loaded hybrid smart with memory V2 RAG service")
except ImportError:
    logger.warning("Hybrid smart with memory V2 RAG service not available")

# Fallback service
if not chat_services:
    logger.error("No RAG services available, using MIA hybrid as fallback")
    chat_services['fallback'] = mia_chat_service_hybrid

@router.post("/chat", response_model=ChatResponse)
async def dynamic_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Dynamic chat endpoint that uses restaurant-specific RAG mode
    """
    try:
        logger.info(f"Dynamic chat request from client {req.client_id} to restaurant {req.restaurant_id}")
        
        # Get restaurant to check its RAG mode
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        
        # Get restaurant's preferred RAG mode
        rag_mode = getattr(restaurant, 'rag_mode', 'hybrid_smart')
        
        # If restaurant doesn't have rag_mode set, use default from env or hybrid_smart
        if not rag_mode:
            rag_mode = os.getenv("DEFAULT_RAG_MODE", "hybrid_smart")
        
        logger.info(f"Restaurant {req.restaurant_id} using RAG mode: {rag_mode}")
        
        # Select appropriate service
        if rag_mode in chat_services:
            chat_service = chat_services[rag_mode]
        else:
            logger.warning(f"RAG mode '{rag_mode}' not available, falling back to hybrid_smart")
            chat_service = chat_services.get('hybrid_smart', chat_services.get('fallback'))
        
        # Get or create client FIRST (before creating message)
        get_or_create_client(db, req.client_id, req.restaurant_id)
        
        # Now create client message
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type=req.sender_type,
            message=req.message
        )
        db.add(new_message)
        db.commit()
        
        # Get AI response using selected service with fallback
        try:
            response = chat_service(req, db)
            
            # Log which service was used
            response_dict = response.dict() if hasattr(response, 'dict') else response
            if isinstance(response_dict, dict) and 'answer' in response_dict:
                logger.info(f"Response generated using {rag_mode} mode")
            
            return response
        except Exception as service_error:
            logger.error(f"Service {rag_mode} failed: {service_error}")
            logger.info("Falling back to MIA hybrid service")
            
            # Fallback to MIA hybrid service
            try:
                fallback_response = mia_chat_service_hybrid(req, db)
                logger.info("Fallback service succeeded")
                return fallback_response
            except Exception as fallback_error:
                logger.error(f"Fallback service also failed: {fallback_error}")
                # Return a basic error response
                from schemas.chat import ChatResponse
                return ChatResponse(answer="I apologize, but I'm experiencing technical difficulties. Please try again later.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dynamic chat endpoint: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/provider")
async def get_provider_info():
    """Get information about available chat providers"""
    return {
        "provider": "dynamic_rag",
        "available_modes": list(chat_services.keys()),
        "default_mode": os.getenv("DEFAULT_RAG_MODE", "hybrid_smart"),
        "features": [
            "Restaurant-specific AI mode selection",
            "Dynamic service routing",
            "Fallback support",
            "All RAG modes available"
        ]
    }