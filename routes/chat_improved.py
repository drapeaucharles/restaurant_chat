"""
Improved chat routes with better AI service integration
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import os

from auth import get_current_restaurant
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from schemas.client import ClientCreateRequest
from services.client_service import create_or_update_client_service

# Dynamic import based on configuration
USE_IMPROVED = os.getenv("USE_IMPROVED_CHAT", "true").lower() == "true"

if USE_IMPROVED:
    from config_improved import get_chat_service, get_chat_provider_info
else:
    from config import get_chat_service, get_chat_provider_info

router = APIRouter(tags=["chat"])


@router.post("/client/create-or-update")
def create_or_update_client(req: ClientCreateRequest, db: Session = Depends(get_db)):
    """Create or update a client."""
    result = create_or_update_client_service(req, db)
    return result


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat requests with improved AI service."""
    print(f"\n🔍 ===== IMPROVED /chat ENDPOINT CALLED =====")
    print(f"📨 Request data: restaurant_id={req.restaurant_id}, client_id={req.client_id}")
    print(f"💬 Message: '{req.message}'")
    print(f"🏷️ Sender Type: {getattr(req, 'sender_type', 'NOT_SET')}")
    print(f"🤖 Using: {'Improved' if USE_IMPROVED else 'Standard'} chat service")
    
    # Enforce default sender_type for public endpoint
    if not hasattr(req, 'sender_type') or not req.sender_type:
        req.sender_type = 'client'
        print(f"⚠️ Missing sender_type! Set default to 'client'")
    
    # Get the appropriate chat service
    chat_service_func = get_chat_service()
    
    # For client messages, save to database first
    if req.sender_type == 'client':
        print(f"💾 Saving client message to database...")
        client_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type=req.sender_type,
            message=req.message
        )
        db.add(client_message)
        db.commit()
        print(f"✅ Client message saved: ID={client_message.id}")
    
    # Process with chat service
    print(f"💬 Processing with chat service...")
    result = chat_service_func(req, db)
    
    # Handle restaurant messages (forward to WhatsApp if applicable)
    if req.sender_type == "restaurant":
        print(f"📱 Restaurant message - checking WhatsApp forwarding...")
        
        client = db.query(models.Client).filter_by(id=req.client_id).first()
        if client and client.phone_number:
            restaurant = db.query(models.Restaurant).filter_by(restaurant_id=req.restaurant_id).first()
            if restaurant and restaurant.whatsapp_session_id:
                # Forward to WhatsApp
                try:
                    import requests
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
                    if response.status_code == 200:
                        print(f"✅ WhatsApp message sent to {client.phone_number}")
                    else:
                        print(f"❌ WhatsApp send failed: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error sending WhatsApp: {str(e)}")
    
    print(f"🤖 Response preview: '{result.answer[:100]}...'")
    print(f"===== END /chat ENDPOINT =====\n")
    
    return result


@router.post("/chat/improved", response_model=ChatResponse)
def chat_improved(
    req: ChatRequest, 
    db: Session = Depends(get_db),
    force_improved: bool = Query(True, description="Force use of improved AI service")
):
    """
    Direct endpoint for improved chat service.
    Useful for A/B testing or gradual rollout.
    """
    print(f"\n🚀 ===== DIRECT IMPROVED CHAT ENDPOINT =====")
    
    # Force use of improved service
    from services.mia_chat_service_improved import mia_chat_service
    
    # Process with improved service
    result = mia_chat_service(req, db)
    
    return result


@router.get("/chat/logs")
def get_chat_logs(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """Get chat logs for a restaurant."""
    print("📥 /chat/logs called")
    
    if current_restaurant.restaurant_id != restaurant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")
    
    # Get messages ordered by timestamp
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.restaurant_id == restaurant_id
    ).order_by(models.ChatMessage.timestamp).all()
    
    # Group messages by client for compatibility
    result = []
    for message in messages:
        if message.sender_type == "client":
            result.append({
                "message": message.message,
                "answer": "",  # Will be filled by next AI message
                "client_id": str(message.client_id),
                "timestamp": message.timestamp.isoformat()
            })
        elif message.sender_type == "ai":
            # Add AI response to most recent client message
            if result and result[-1]["client_id"] == str(message.client_id) and not result[-1]["answer"]:
                result[-1]["answer"] = message.message
            else:
                # Standalone AI message
                result.append({
                    "message": "",
                    "answer": message.message,
                    "client_id": str(message.client_id),
                    "timestamp": message.timestamp.isoformat()
                })
    
    return result


@router.get("/chat-provider-info")
def get_provider_info():
    """Get information about the current chat provider."""
    info = get_chat_provider_info()
    info["improved_endpoint_available"] = True
    return info


@router.get("/chat/test-comparison")
def test_comparison(
    query: str = Query(..., description="Test query to compare services"),
    db: Session = Depends(get_db)
):
    """
    Compare standard vs improved chat service responses.
    Useful for testing and debugging.
    """
    # Test restaurant ID
    test_restaurant_id = "bella_vista_restaurant"
    test_client_id = "test-comparison-client"
    
    # Create test request
    test_req = ChatRequest(
        restaurant_id=test_restaurant_id,
        client_id=test_client_id,
        sender_type="client",
        message=query
    )
    
    results = {}
    
    # Test standard service
    try:
        from services.mia_chat_service import mia_chat_service as standard_service
        standard_result = standard_service(test_req, db)
        results["standard"] = {
            "answer": standard_result.answer,
            "length": len(standard_result.answer),
            "service": "mia_chat_service"
        }
    except Exception as e:
        results["standard"] = {"error": str(e)}
    
    # Test improved service
    try:
        from services.mia_chat_service_improved import mia_chat_service as improved_service
        improved_result = improved_service(test_req, db)
        results["improved"] = {
            "answer": improved_result.answer,
            "length": len(improved_result.answer),
            "service": "mia_chat_service_improved"
        }
    except Exception as e:
        results["improved"] = {"error": str(e)}
    
    # Clean up test messages
    db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == test_client_id
    ).delete()
    db.commit()
    
    return {
        "query": query,
        "results": results
    }