"""
Chat routes with MIA integration support
Uses configuration to switch between OpenAI and MIA
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_restaurant
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from schemas.client import ClientCreateRequest
from services.client_service import create_or_update_client_service
from config import get_chat_service, get_chat_provider_info, ENABLE_CHAT_LOGGING
import logging

router = APIRouter(tags=["chat"])
logger = logging.getLogger(__name__)

# Get the configured chat service
chat_service = get_chat_service()

@router.get("/chat/provider")
def get_provider_info():
    """Get information about the current chat provider"""
    return get_chat_provider_info()

@router.post("/client/create-or-update")
def create_or_update_client(req: ClientCreateRequest, db: Session = Depends(get_db)):
    """Create or update a client."""
    result = create_or_update_client_service(req, db)
    return result

@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat requests using configured provider (MIA or OpenAI)."""
    
    if ENABLE_CHAT_LOGGING:
        logger.info(f"Chat endpoint called - Provider: {get_chat_provider_info()['provider']}")
        logger.info(f"Request: restaurant_id={req.restaurant_id}, client_id={req.client_id}")
        logger.info(f"Message: '{req.message}'")
    
    # Enforce default sender_type for public endpoint
    if not hasattr(req, 'sender_type') or not req.sender_type:
        req.sender_type = 'client'
        logger.info("Missing sender_type - defaulting to 'client'")
    
    # Save client message before AI processing
    from services.mia_chat_service import get_or_create_client
    
    # Ensure client exists
    client = get_or_create_client(db, req.client_id, req.restaurant_id)
    
    # Save the incoming message
    client_message = models.ChatMessage(
        restaurant_id=req.restaurant_id,
        client_id=req.client_id,
        sender_type=req.sender_type,
        message=req.message
    )
    db.add(client_message)
    db.commit()
    db.refresh(client_message)
    
    if ENABLE_CHAT_LOGGING:
        logger.info(f"Client message saved: ID={client_message.id}")
    
    # Use configured chat service (MIA or OpenAI)
    result = chat_service(req, db)
    
    # Handle WhatsApp forwarding for restaurant messages
    if req.sender_type == "restaurant":
        client = db.query(models.Client).filter_by(id=req.client_id).first()
        if client and client.phone_number:
            restaurant = db.query(models.Restaurant).filter_by(restaurant_id=req.restaurant_id).first()
            if restaurant and restaurant.whatsapp_session_id:
                # Forward to WhatsApp
                import requests
                import os
                
                def send_whatsapp_message():
                    try:
                        whatsapp_url = f"{os.getenv('PUBLIC_API_URL', 'http://localhost:8000')}/whatsapp/send"
                        payload = {
                            "session_id": restaurant.whatsapp_session_id,
                            "to_number": client.phone_number,
                            "message": req.message
                        }
                        headers = {
                            "X-API-Key": os.getenv("WHATSAPP_API_KEY", "supersecretkey123"),
                            "Content-Type": "application/json"
                        }
                        
                        response = requests.post(whatsapp_url, json=payload, headers=headers, timeout=10)
                        
                        if ENABLE_CHAT_LOGGING:
                            if response.status_code == 200:
                                logger.info("WhatsApp message sent successfully")
                            else:
                                logger.error(f"WhatsApp send failed: {response.status_code}")
                                
                    except Exception as e:
                        logger.error(f"Error sending WhatsApp message: {str(e)}")
                
                send_whatsapp_message()
    
    if ENABLE_CHAT_LOGGING:
        logger.info(f"AI Response length: {len(result.answer)}")
    
    return result

@router.get("/chat/logs")
def get_chat_logs(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """Get chat logs for a restaurant"""
    
    if current_restaurant.restaurant_id != restaurant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")
    
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.restaurant_id == restaurant_id
    ).order_by(models.ChatMessage.timestamp).all()
    
    # Format for compatibility
    result = []
    for message in messages:
        if message.sender_type == "client":
            result.append({
                "message": message.message,
                "answer": "",
                "client_id": str(message.client_id),
                "timestamp": message.timestamp.isoformat()
            })
        elif message.sender_type == "ai":
            if result and result[-1]["client_id"] == str(message.client_id) and not result[-1]["answer"]:
                result[-1]["answer"] = message.message
            else:
                result.append({
                    "message": "",
                    "answer": message.message,
                    "client_id": str(message.client_id),
                    "timestamp": message.timestamp
                })
    
    return result