"""
Chat endpoint with context-enhanced orchestration
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse
from database import get_db
from services.mia_chat_service_context_enhanced import mia_chat_service_context_enhanced
import models
import logging
from datetime import datetime
import uuid

logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/chat/context-enhanced", response_model=ChatResponse, tags=["chat"])
async def chat_context_enhanced(request: ChatRequest, db: Session = Depends(get_db)):
    """
    Chat endpoint with enhanced context retention.
    Features:
    - Context State Line tracking
    - Pronoun resolution
    - Category and diet persistence
    - Dynamic temperature settings
    """
    try:
        # Log incoming request
        logger.info(f"Context-enhanced chat request from client {request.client_id} for restaurant {request.restaurant_id}")
        
        # Validate restaurant exists
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == request.restaurant_id
        ).first()
        
        if not restaurant:
            raise HTTPException(status_code=404, detail="Restaurant not found")
        
        # Store the incoming message
        chat_message = models.ChatMessage(
            message_id=str(uuid.uuid4()),
            restaurant_id=request.restaurant_id,
            client_id=request.client_id,
            message=request.message,
            sender_type="client",
            timestamp=datetime.utcnow(),
            metadata=request.metadata
        )
        db.add(chat_message)
        db.commit()
        
        # Generate response using context-enhanced service
        response = mia_chat_service_context_enhanced(request, db)
        
        # Store AI response
        ai_message = models.ChatMessage(
            message_id=str(uuid.uuid4()),
            restaurant_id=request.restaurant_id,
            client_id=request.client_id,
            message=response.answer,
            sender_type="ai",
            timestamp=datetime.utcnow(),
            metadata=response.metadata if hasattr(response, 'metadata') else {}
        )
        db.add(ai_message)
        db.commit()
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in context-enhanced chat: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/chat/context-enhanced/health", tags=["chat"])
async def health_check():
    """Check if context-enhanced chat service is available"""
    return {"status": "healthy", "service": "chat-context-enhanced"}