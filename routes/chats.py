"""
Chat management routes and endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from sqlalchemy.sql import func, desc
from database import get_db
import models
from schemas.chat import ChatMessageCreate, ChatMessageResponse
from auth import get_current_restaurant
from schemas.chat import ToggleAIRequest


router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatMessageResponse)
def create_chat_message(
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db)
):
    """Store a new chat message."""
    print(f"\n🔍 ===== NEW /chat/ POST ENDPOINT CALLED =====")
    print(f"📨 Message data received: {message_data}")
    print(f"🏷️ Sender Type: {message_data.sender_type}")
    print(f"💬 Message: '{message_data.message}'")
    print(f"🏪 Restaurant ID: {message_data.restaurant_id}")
    print(f"👤 Client ID: {message_data.client_id}")
    
    # Verify restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == message_data.restaurant_id
    ).first()

    if not restaurant:
        print(f"❌ Restaurant not found: {message_data.restaurant_id}")
        raise HTTPException(status_code=404, detail="Restaurant not found")

    print(f"✅ Restaurant found: {restaurant.restaurant_id}")

    # Check if client exists
    client = db.query(models.Client).filter(
        models.Client.id == message_data.client_id
    ).first()

    # ✅ Auto-create the client if not found
    if not client:
        print(f"🆕 Creating new client: {message_data.client_id}")
        client = models.Client(
            id=message_data.client_id,
            restaurant_id=message_data.restaurant_id
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        print(f"✅ Created new client: {client.id}")
    else:
        print(f"✅ Existing client found: {client.id}")

    # Verify client belongs to the restaurant
    if client.restaurant_id != message_data.restaurant_id:
        print(f"❌ Client {client.id} does not belong to restaurant {message_data.restaurant_id}")
        raise HTTPException(status_code=403, detail="Client does not belong to this restaurant")

    # Create new chat message
    print(f"💾 Creating ChatMessage with sender_type: '{message_data.sender_type}'")
    new_message = models.ChatMessage(
        restaurant_id=message_data.restaurant_id,
        client_id=message_data.client_id,
        sender_type=message_data.sender_type,  # ✅ VERIFIED: Store sender_type from request
        message=message_data.message
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    
    print(f"✅ STORED MESSAGE IN DATABASE:")
    print(f"   - ID: {new_message.id}")
    print(f"   - sender_type: '{new_message.sender_type}'")
    print(f"   - message: '{new_message.message[:50]}...'")
    print(f"   - timestamp: {new_message.timestamp}")

    response = ChatMessageResponse(
        id=new_message.id,
        restaurant_id=new_message.restaurant_id,
        client_id=new_message.client_id,
        sender_type=new_message.sender_type,  # ✅ VERIFIED: Return sender_type in response
        message=new_message.message,
        timestamp=new_message.timestamp
    )
    
    print(f"📤 Returning response with sender_type: '{response.sender_type}'")
    print(f"===== END /chat/ POST ENDPOINT =====\n")

    return response


@router.get("/", response_model=List[ChatMessageResponse])
def get_chat_messages(
    restaurant_id: str,
    client_id: uuid.UUID,
    db: Session = Depends(get_db)
):
    """Get all chat messages between a client and restaurant."""
    # Verify restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Verify client exists and belongs to the restaurant
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.restaurant_id == restaurant_id
    ).first()

    if not client:
        raise HTTPException(status_code=404, detail="Client not found or does not belong to this restaurant")

    # Get all chat messages between the client and restaurant, ordered by timestamp
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.client_id == client_id
    ).order_by(models.ChatMessage.timestamp).all()

    return [
        ChatMessageResponse(
            id=message.id,
            restaurant_id=message.restaurant_id,
            client_id=message.client_id,
            sender_type=message.sender_type,
            message=message.message,
            timestamp=message.timestamp
        )
        for message in messages
    ]


@router.get("/logs/latest")
def get_latest_logs_grouped_by_client(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    if current_restaurant.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    print(f"🔍 /logs/latest called for restaurant: {restaurant_id}")

    # ✅ FIXED: Get latest messages from ChatMessage table instead of ChatLog
    # First, get subquery of latest message timestamps per client
    latest_subquery = (
        db.query(
            models.ChatMessage.client_id,
            func.max(models.ChatMessage.timestamp).label("latest_ts")
        )
        .filter(models.ChatMessage.restaurant_id == restaurant_id)
        .group_by(models.ChatMessage.client_id)
        .subquery()
    )

    # Join to the actual ChatMessage table on both client_id and timestamp
    messages = (
        db.query(models.ChatMessage)
        .join(
            latest_subquery,
            (models.ChatMessage.client_id == latest_subquery.c.client_id) &
            (models.ChatMessage.timestamp == latest_subquery.c.latest_ts)
        )
        .order_by(desc(models.ChatMessage.timestamp))
        .all()
    )

    print(f"📋 Found {len(messages)} latest messages from ChatMessage table")

    result = []
    for message in messages:
        print(f"📨 Latest message: client_id={message.client_id}, sender_type={message.sender_type}, message='{message.message[:50]}...'")
        result.append({
            "client_id": str(message.client_id),
            "table_id": getattr(message, 'table_id', ''),  # ChatMessage may not have table_id
            "message": message.message,
            "answer": "",  # ChatMessage doesn't have separate answer field
            "timestamp": message.timestamp,
            "ai_enabled": True,  # Default to True for ChatMessage entries
            "sender_type": message.sender_type  # ✅ Use actual sender_type from database
        })

    print(f"📋 Returning {len(result)} latest messages with preserved sender_type")
    return result


@router.get("/logs/client")
def get_full_chat_history_for_client(
    restaurant_id: str,
    client_id: str,
    db: Session = Depends(get_db)
):
    """
    Get full chat history for a specific client.
    Public endpoint - no authentication required.
    Security: Client must belong to the specified restaurant.
    Auto-creates client if they don't exist (for first-time visitors).
    """
    print(f"\n🔍 ===== /logs/client ENDPOINT CALLED =====")
    print(f"🏪 Restaurant ID: {restaurant_id}")
    print(f"👤 Client ID: {client_id}")
    
    # ✅ First, verify the restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        print(f"❌ Restaurant not found: {restaurant_id}")
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    print(f"✅ Restaurant found: {restaurant.restaurant_id}")
    
    # ✅ Check if client exists, create if not (for first-time visitors)
    client = db.query(models.Client).filter(
        models.Client.id == client_id,
        models.Client.restaurant_id == restaurant_id
    ).first()
    
    if not client:
        # ✅ Auto-create client for first-time visitors
        print(f"🆕 Creating new client {client_id} for restaurant {restaurant_id}")
        client = models.Client(
            id=client_id,
            restaurant_id=restaurant_id
        )
        db.add(client)
        db.commit()
        db.refresh(client)
        print(f"✅ Created new client: {client.id}")
    else:
        print(f"✅ Existing client found: {client.id}")
    
    # ✅ VERIFIED: Get messages from ChatMessage table (new) instead of ChatLog (legacy)
    print(f"📋 Querying ChatMessage table for messages...")
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.client_id == client_id
    ).order_by(models.ChatMessage.timestamp).all()
    
    print(f"📋 Found {len(messages)} messages in ChatMessage table for client {client_id}")

    # ✅ VERIFIED: Return messages with proper sender_type preservation
    full_log = []
    for message in messages:
        print(f"📨 Message #{len(full_log)+1}: sender_type='{message.sender_type}', message='{message.message[:50]}...', timestamp={message.timestamp}")
        
        # Verify sender_type is not None or empty
        if not message.sender_type:
            print(f"⚠️ WARNING: Message {message.id} has empty/null sender_type!")
        
        full_log.append({
            "client_id": str(message.client_id),
            "table_id": getattr(message, 'table_id', ''),  # ChatMessage may not have table_id
            "message": message.message,
            "timestamp": message.timestamp,
            "sender_type": message.sender_type,  # ✅ VERIFIED: Use actual sender_type from database
        })

    print(f"📤 Returning {len(full_log)} messages with preserved sender_type")
    print(f"🔍 sender_type distribution:")
    sender_types = {}
    for msg in full_log:
        sender_type = msg['sender_type'] or 'NULL'
        sender_types[sender_type] = sender_types.get(sender_type, 0) + 1
    for st, count in sender_types.items():
        print(f"   - {st}: {count} messages")
    
    print(f"===== END /logs/client ENDPOINT =====\n")
    return full_log


@router.post("/logs/toggle-ai")
def toggle_ai_for_conversation(
    payload: ToggleAIRequest,
    db: Session = Depends(get_db),
    current_restaurant: models.Restaurant = Depends(get_current_restaurant)
):
    if current_restaurant.restaurant_id != payload.restaurant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    db.query(models.ChatLog).filter(
        models.ChatLog.restaurant_id == payload.restaurant_id,
        models.ChatLog.client_id == payload.client_id
    ).update({"ai_enabled": payload.enabled})
    db.commit()
    return {"status": "ok", "enabled": payload.enabled}
