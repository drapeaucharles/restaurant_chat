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

# V7 removed - using V5 with proper goodbye handling

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
            SELECT type 
            FROM businesses 
            WHERE business_id = :business_id
        """)
        business_result = db.execute(business_query, {"business_id": req.restaurant_id}).fetchone()
        
        if business_result:
            business_type = business_result[0]
            rag_mode = None  # Will be set from restaurants table if needed
            logger.info(f"Business {req.restaurant_id} is type '{business_type}'")
        else:
            business_type = None
            logger.info(f"Business {req.restaurant_id} not found in businesses table")
            
        # Check if this is a visa agency - use AI-powered visa chat service
        logger.info(f"🔍 ROUTING DEBUG: business_type='{business_type}', checking if visa_agency or legal_visa")
        if business_type in ['visa_agency', 'legal_visa']:
            logger.info(f"✅ VISA AGENCY DETECTED! Using AI-powered visa chat service")
            try:
                logger.info(f"🔧 DEBUG: Importing hybrid_visa_chat_service...")
                from services.visa_chat_service_hybrid import hybrid_visa_chat_service
                selected_service = hybrid_visa_chat_service
                logger.info(f"✅ SUCCESS: Selected HYBRID visa chat service for {req.restaurant_id}")
                logger.info(f"🎯 DEBUG: selected_service = {selected_service}")
            except ImportError as e:
                logger.error(f"❌ IMPORT ERROR: AI visa chat service not available: {e}, falling back to default")
                selected_service = chat_services.get('default', chat_services.get('fallback'))
            except Exception as e:
                logger.error(f"❌ UNEXPECTED ERROR: {e}, falling back to default")
                selected_service = chat_services.get('default', chat_services.get('fallback'))
        elif business_result:
            # Regular business - get rag_mode from restaurants table
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if restaurant:
                rag_mode = restaurant.rag_mode or 'default'
                logger.info(f"Regular business using rag_mode: {rag_mode}")
                
                if rag_mode in chat_services:
                    selected_service = chat_services[rag_mode]
                    logger.info(f"Selected service: {rag_mode}")
                else:
                    logger.warning(f"RAG mode '{rag_mode}' not available, falling back to default")
                    selected_service = chat_services.get('default', chat_services.get('fallback'))
            else:
                logger.warning(f"Business {req.restaurant_id} not found in restaurants table")
                selected_service = chat_services.get('default', chat_services.get('fallback'))
        else:
            # Fallback to restaurant model for backward compatibility
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                raise HTTPException(status_code=404, detail="Restaurant/Business not found")
            
            rag_mode = getattr(restaurant, 'rag_mode', 'internal_tools_v5')
            business_type = getattr(restaurant, 'business_type', 'restaurant')
            
            # If restaurant doesn't have rag_mode set, use default
            if not rag_mode:
                rag_mode = os.getenv("DEFAULT_RAG_MODE", "internal_tools_v5")
            
            logger.info(f"Restaurant {req.restaurant_id} using RAG mode: {rag_mode}")
            
            # Check if this is a visa agency in restaurants table
            if business_type in ['visa_agency', 'legal_visa']:
                logger.info(f"Visa agency detected in restaurants table, using full flows visa chat service")
                try:
                    from services.visa_chat_service_full_flows import full_flows_visa_chat_service
                    selected_service = full_flows_visa_chat_service
                    logger.info(f"Selected full flows visa chat service for {req.restaurant_id}")
                except ImportError as e:
                    logger.warning(f"Visa chat service not available: {e}, falling back to default")
                    selected_service = chat_services.get('default', chat_services.get('fallback'))
            else:
                # Regular restaurant - use rag_mode
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
            logger.info(f"🚀 DEBUG: About to call selected_service: {selected_service}")
            logger.info(f"📞 DEBUG: Calling service with req.restaurant_id={req.restaurant_id}, req.message='{req.message[:50]}...'")
            response = selected_service(req, db)
            logger.info(f"✅ DEBUG: Service call completed, response type: {type(response)}")
            logger.info(f"📄 DEBUG: Response answer: '{response.answer[:100]}...'")
            
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