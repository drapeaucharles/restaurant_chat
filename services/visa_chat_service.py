# services/visa_chat_service.py
"""
Visa Agency Chat Service
Integrates visa flows with the existing chat system
Feature-flagged and backwards compatible
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from config import MIA_VISA_ENABLED
from schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


def visa_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Main visa chat service entry point
    Handles visa agency conversations with multi-flow orchestration
    
    Args:
        req: Chat request with message, client_id, restaurant_id
        db: Database session
    
    Returns:
        ChatResponse with AI-generated response
    """
    try:
        # Check if visa functionality is enabled
        if not MIA_VISA_ENABLED:
            return ChatResponse(
                answer="Visa services are not currently available. Please contact support.",
                response_id=None,
                confidence_score=0.0
            )
        
        # Check if this is a visa agency business
        business_type = get_business_type(db, req.restaurant_id)
        if business_type != 'visa_agency':
            # Fall back to restaurant chat service
            from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5
            return mia_chat_service_internal_tools_v5(req, db)
        
        # Import visa flow orchestrator
        from services.visa.v1.flows import VisaFlowOrchestrator
        
        # Get chat history
        chat_history = get_chat_history(db, req.client_id, req.restaurant_id)
        
        # Initialize flow orchestrator
        orchestrator = VisaFlowOrchestrator(db, req.restaurant_id)
        
        # Process message through visa flows
        result = orchestrator.process_message(
            message=req.message,
            client_id=req.client_id,
            chat_history=chat_history
        )
        
        # Save conversation to database
        save_chat_message(db, req.client_id, req.restaurant_id, req.message, "client")
        save_chat_message(db, req.client_id, req.restaurant_id, result["answer"], "ai")
        
        # Return response
        return ChatResponse(
            answer=result["answer"],
            response_id=result.get("flow_used"),
            confidence_score=0.9  # High confidence for structured flows
        )
        
    except Exception as e:
        logger.error(f"Error in visa chat service: {str(e)}")
        return ChatResponse(
            answer="I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa inquiry.",
            response_id="error",
            confidence_score=0.0
        )


def get_business_type(db: Session, business_id: str) -> str:
    """
    Get business type for the given business ID
    Checks both new businesses table and restaurant extensions
    """
    try:
        # First check if MIA_VISA_ENABLED to avoid import errors
        if not MIA_VISA_ENABLED:
            return 'restaurant'
        
        # Use raw SQL to check businesses table (same as routing logic)
        from sqlalchemy import text
        business_query = text("""
            SELECT business_type 
            FROM businesses 
            WHERE business_id = :business_id
        """)
        business_result = db.execute(business_query, {"business_id": business_id}).fetchone()
        
        if business_result:
            return business_result[0]
        
        # Fallback: check restaurants table
        restaurant_query = text("""
            SELECT business_type 
            FROM restaurants 
            WHERE restaurant_id = :restaurant_id
        """)
        restaurant_result = db.execute(restaurant_query, {"restaurant_id": business_id}).fetchone()
        
        if restaurant_result and restaurant_result[0]:
            return restaurant_result[0]
        
        # Default to restaurant
        return 'restaurant'
        
    except Exception as e:
        logger.warning(f"Error getting business type: {str(e)}")
        return 'restaurant'


def get_chat_history(db: Session, client_id: str, business_id: str, limit: int = 10) -> list:
    """
    Get recent chat history for context
    """
    try:
        import models
        
        messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.client_id == client_id,
            models.ChatMessage.restaurant_id == business_id
        ).order_by(models.ChatMessage.timestamp.desc()).limit(limit * 2).all()
        
        history = []
        for msg in reversed(messages):
            history.append({
                "role": "user" if msg.sender_type in ["customer", "client"] else "assistant",
                "message": msg.message
            })
        
        return history[-limit:]
        
    except Exception as e:
        logger.warning(f"Error getting chat history: {str(e)}")
        return []


def save_chat_message(db: Session, client_id: str, business_id: str, message: str, sender_type: str):
    """
    Save chat message to database
    """
    try:
        import models
        
        chat_message = models.ChatMessage(
            restaurant_id=business_id,
            client_id=client_id,
            sender_type=sender_type,
            message=message
        )
        
        db.add(chat_message)
        db.commit()
        
    except Exception as e:
        logger.warning(f"Error saving chat message: {str(e)}")
        db.rollback()


# Backwards compatibility - export as main chat service when visa is enabled
def get_chat_service():
    """
    Get appropriate chat service based on configuration
    Returns visa chat service if enabled, otherwise falls back to restaurant service
    """
    if MIA_VISA_ENABLED:
        return visa_chat_service
    else:
        from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5
        return mia_chat_service_internal_tools_v5
