"""
Dynamic chat endpoint that uses restaurant-specific RAG mode
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from datetime import datetime
from services.chat_service import chat_service, get_or_create_client
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Import only available services
chat_services = {}

# Default service - using V5 as stable baseline
try:
    from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5
    chat_services['internal_tools_v5'] = mia_chat_service_internal_tools_v5
    chat_services['default'] = mia_chat_service_internal_tools_v5
    logger.info("Loaded internal tools service V5 (default)")
except ImportError as e:
    logger.warning(f"Internal tools V5 service not available: {str(e)}")

# V6 is broken - DO NOT USE
# V6 has wrong field names causing 0 results and AI hallucination

# V7 available but not default
try:
    from services.mia_chat_service_internal_tools_v7 import mia_chat_service_internal_tools_v7
    chat_services['internal_tools_v7'] = mia_chat_service_internal_tools_v7
    logger.info("Loaded internal tools service V7")
except ImportError as e:
    logger.warning(f"Internal tools V7 service not available: {str(e)}")

# RAG services that exist
try:
    from services.rag_chat_service import rag_enhanced_chat_service
    chat_services['rag'] = rag_enhanced_chat_service
    logger.info("Loaded RAG service")
except ImportError as e:
    logger.warning(f"RAG service not available: {str(e)}")

try:
    from services.rag_chat_service_improved import rag_enhanced_chat_service_improved
    chat_services['rag_improved'] = rag_enhanced_chat_service_improved
    logger.info("Loaded improved RAG service")
except ImportError as e:
    logger.warning(f"Improved RAG service not available: {str(e)}")

# Fallback service
if not chat_services:
    logger.error("No chat services available, using base chat_service as fallback")
    chat_services['fallback'] = chat_service
else:
    # Always have fallback available
    chat_services['fallback'] = chat_service

logger.info(f"Available chat services: {list(chat_services.keys())}")

@router.post("/chat", response_model=ChatResponse)
async def dynamic_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Dynamic chat endpoint that uses restaurant-specific RAG mode
    """
    try:
        logger.info(f"🔵 CHAT REQUEST RECEIVED: client={req.client_id}, restaurant={req.restaurant_id}, message='{req.message[:50]}...'")
        
        # Get restaurant/business to check its RAG mode
        # First try businesses table (new universal model)
        from sqlalchemy import text
        business_query = text("""
            SELECT business_type, rag_mode 
            FROM businesses 
            WHERE business_id = :business_id
        """)
        business_result = db.execute(business_query, {"business_id": req.restaurant_id}).fetchone()
        
        if business_result:
            business_type, rag_mode = business_result
            logger.info(f"Business {req.restaurant_id} is type '{business_type}' with rag_mode '{rag_mode}'")
        else:
            # Fallback to restaurant model for backward compatibility
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                raise HTTPException(status_code=404, detail="Restaurant/Business not found")
            
            rag_mode = getattr(restaurant, 'rag_mode', 'internal_tools_v5')
        
        # If restaurant doesn't have rag_mode set, use default
        if not rag_mode:
            rag_mode = os.getenv("DEFAULT_RAG_MODE", "internal_tools_v5")
        
        logger.info(f"Restaurant {req.restaurant_id} using RAG mode: {rag_mode}")
        
        # Select appropriate service
        if rag_mode in chat_services:
            selected_service = chat_services[rag_mode]
            logger.info(f"Selected service: {rag_mode}")
        else:
            logger.warning(f"RAG mode '{rag_mode}' not available, falling back to default")
            selected_service = chat_services.get('default', chat_services.get('fallback'))
        
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
            response = selected_service(req, db)
            
            # Log which service was used
            logger.info(f"Response generated using {rag_mode} mode")
            
            return response
        except Exception as service_error:
            logger.error(f"Service {rag_mode} failed: {service_error}")
            logger.info("Falling back to default service")
            
            # Fallback to default service
            try:
                fallback_response = chat_services['fallback'](req, db)
                logger.info("Fallback service succeeded")
                return fallback_response
            except Exception as fallback_error:
                logger.error(f"Fallback service also failed: {fallback_error}")
                raise HTTPException(
                    status_code=500,
                    detail="Chat service temporarily unavailable"
                )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dynamic chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/chat/available-modes")
async def get_available_modes():
    """Get list of available chat modes"""
    return {
        "available_modes": list(chat_services.keys()),
        "default_mode": "internal_tools_v5"
    }