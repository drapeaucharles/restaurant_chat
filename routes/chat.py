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
    
    # 🔧 FIX: Save client message to ChatMessage table BEFORE AI processing
    from services.chat_service import get_or_create_client
    
    # Ensure client exists
    client = get_or_create_client(db, req.client_id, req.restaurant_id)
    print(f"✅ Client ensured: {client.id}")
    
    # Save the incoming message to ChatMessage table
    print(f"💾 Saving client message to ChatMessage table...")
    client_message = models.ChatMessage(
        restaurant_id=req.restaurant_id,
        client_id=req.client_id,
        sender_type=req.sender_type,
        message=req.message
    )
    db.add(client_message)
    db.commit()
    db.refresh(client_message)
    print(f"✅ Client message saved: ID={client_message.id}, sender_type='{client_message.sender_type}'")
    
    # Call chat service for AI response (if appropriate)
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
    
    # ✅ MIGRATED: Use ChatMessage instead of ChatLog
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.restaurant_id == restaurant_id
    ).order_by(models.ChatMessage.timestamp).all()
    
    # Group messages by client and format for compatibility
    result = []
    for message in messages:
        # For client messages, include the message
        # For AI messages, treat as "answer" to previous client message
        if message.sender_type == "client":
            result.append({
                "message": message.message,
                "answer": "",  # Will be filled by next AI message if exists
                "client_id": str(message.client_id),
                "timestamp": message.timestamp
            })
        elif message.sender_type == "ai":
            # Find the most recent client message for this client and add the AI answer
            if result and result[-1]["client_id"] == str(message.client_id) and not result[-1]["answer"]:
                result[-1]["answer"] = message.message
            else:
                # AI message without preceding client message - create entry
                result.append({
                    "message": "",
                    "answer": message.message,
                    "client_id": str(message.client_id),
                    "timestamp": message.timestamp
                })
    
    return result
