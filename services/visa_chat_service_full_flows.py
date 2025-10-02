# services/visa_chat_service_full_flows.py
"""
Full Visa Chat Service with 7-Step Flow Orchestration
Uses working flow orchestrator with all 7 visa flows
"""

import logging
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import text
from config import MIA_VISA_ENABLED
from schemas.chat import ChatRequest, ChatResponse
from .visa_flow_orchestrator_working import WorkingVisaFlowOrchestrator

logger = logging.getLogger(__name__)


def full_flows_visa_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Full visa chat service with 7-step flow orchestration
    Router → Profiler → Normalizer → Recommender → Clarifier → Explainer → Tracker
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
        business_type = get_business_type_sql(db, req.restaurant_id)
        if business_type != 'visa_agency':
            # Fall back to restaurant chat service
            from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5
            return mia_chat_service_internal_tools_v5(req, db)
        
        # Get chat history for context
        chat_history = get_chat_history_sql(db, req.client_id, req.restaurant_id)
        
        # Use hybrid visa chat service (orchestrator + AI)
        logger.info(f"🔍 DEBUG: About to import hybrid_visa_chat_service")
        from services.visa_chat_service_hybrid import hybrid_visa_chat_service
        logger.info(f"✅ DEBUG: Successfully imported hybrid_visa_chat_service")
        
        logger.info(f"🎯 Using hybrid visa service (orchestrator + AI) for {req.restaurant_id}")
        logger.info(f"🔍 DEBUG: Calling hybrid_visa_chat_service with message: '{req.message[:50]}...'")
        
        result = hybrid_visa_chat_service(req, db)
        logger.info(f"✅ DEBUG: Hybrid service returned: '{result.answer[:50]}...'")
        return result
        
    except Exception as e:
        logger.error(f"Error in full flows visa chat service: {str(e)}")
        return ChatResponse(
            answer="I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa inquiry.",
            response_id="error",
            confidence_score=0.0
        )


def get_business_type_sql(db: Session, business_id: str) -> str:
    """Get business type using raw SQL"""
    try:
        query = text("SELECT business_type FROM businesses WHERE business_id = :business_id")
        result = db.execute(query, {"business_id": business_id}).fetchone()
        return result[0] if result else 'restaurant'
    except Exception as e:
        logger.error(f"Error getting business type: {e}")
        return 'restaurant'


def get_chat_history_sql(db: Session, client_id: str, restaurant_id: str, limit: int = 10) -> List[Dict]:
    """Get recent chat history using raw SQL"""
    try:
        query = text("""
            SELECT sender_type, message, timestamp
            FROM chat_messages 
            WHERE client_id = :client_id AND restaurant_id = :restaurant_id
            ORDER BY timestamp DESC 
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "client_id": client_id,
            "restaurant_id": restaurant_id,
            "limit": limit
        }).fetchall()
        
        history = []
        for row in reversed(results):  # Reverse to get chronological order
            history.append({
                "role": "user" if row[0] == "client" else "assistant",
                "message": row[1],
                "timestamp": row[2].isoformat() if row[2] else None
            })
        
        return history
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return []


def save_chat_message_sql(db: Session, client_id: str, restaurant_id: str, message: str, sender_type: str):
    """Save chat message using ORM with proper error handling"""
    try:
        import models
        
        new_message = models.ChatMessage(
            restaurant_id=restaurant_id,
            client_id=client_id,
            sender_type=sender_type,
            message=message
        )
        db.add(new_message)
        db.commit()
        
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        try:
            db.rollback()
            logger.info("Chat message transaction rolled back")
        except Exception as rollback_error:
            logger.error(f"Chat message rollback failed: {rollback_error}")
