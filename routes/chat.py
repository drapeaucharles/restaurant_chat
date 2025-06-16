"""
Chat-related routes and endpoints.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from auth import get_current_restaurant
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from schemas.client import ClientCreateRequest
from services.chat_service import chat_service
from services.client_service import create_or_update_client_service

router = APIRouter(tags=["chat"])


@router.post("/client/create-or-update")
def create_or_update_client(req: ClientCreateRequest, db: Session = Depends(get_db)):
    """Create or update a client."""
    result = create_or_update_client_service(req, db)
    return result


@router.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Handle chat requests."""
    print(f"\n🔍 ===== LEGACY /chat ENDPOINT CALLED =====")
    print(f"📨 Request data: restaurant_id={req.restaurant_id}, client_id={req.client_id}")
    print(f"💬 Message: '{req.message}'")
    print(f"🏷️ Sender Type from request: {getattr(req, 'sender_type', 'NOT_SET')}")
    
    # ✅ VERIFIED: Enforce default sender_type for public /chat endpoint
    original_sender_type = getattr(req, 'sender_type', None)
    if not hasattr(req, 'sender_type') or not req.sender_type:
        req.sender_type = 'client'
        print(f"⚠️ Missing sender_type! Set default to 'client' for public endpoint")
    else:
        print(f"✅ sender_type provided: '{req.sender_type}'")
    
    print(f"📋 Final sender_type for processing: '{req.sender_type}'")
    
    # Call chat service and log result
    result = chat_service(req, db)
    
    print(f"🤖 AI Response: '{result.answer[:100]}...' (length: {len(result.answer)})")
    print(f"🔍 Response empty: {len(result.answer) == 0}")
    print(f"===== END /chat ENDPOINT =====\n")
    
    return result


@router.get("/chat/logs")
def get_chat_logs(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    print("📥 /chat/logs called")
    print("🔍 Provided restaurant_id:", restaurant_id)
    print("🔐 Authenticated restaurant_id:", current_restaurant.restaurant_id)

    if current_restaurant.restaurant_id != restaurant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")
    
    logs = db.query(models.ChatLog).filter(
        models.ChatLog.restaurant_id == restaurant_id
    ).all()
    
    return [
        {
            "message": log.message,
            "answer": log.answer,
            "client_id": str(log.client_id),
            "timestamp": log.timestamp
        }
        for log in logs
    ]
