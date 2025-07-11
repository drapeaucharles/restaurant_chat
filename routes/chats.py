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
from services.chat_service import get_or_create_client


router = APIRouter(tags=["chat-management"])


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
    client = get_or_create_client(db, message_data.client_id, message_data.restaurant_id)
    print(f"✅ Ensured client exists: {client.id}")


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

    # 🔧 FIX: If this is a client message, trigger AI response via chat_service
    ai_response = ""
    if message_data.sender_type == "client":
        print(f"🤖 Client message detected - checking if AI should respond...")
        
        # Create ChatRequest for AI processing
        from schemas.chat import ChatRequest
        chat_request = ChatRequest(
            restaurant_id=message_data.restaurant_id,
            client_id=message_data.client_id,
            message=message_data.message,
            sender_type=message_data.sender_type
        )
        
        # Import and call chat_service for AI response
        from services.chat_service import chat_service
        ai_result = chat_service(chat_request, db)
        ai_response = ai_result.answer
        
        if ai_response:
            print(f"✅ AI responded with: '{ai_response[:50]}...'")
        else:
            print(f"ℹ️ AI did not respond (disabled or blocked)")

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

    print(f"🔍 /logs/latest (ChatMessage version) called for restaurant: {restaurant_id}")

    # 🔧 FIX: Get last 2 messages per client instead of just 1
    # First, get all clients for this restaurant
    clients = db.query(models.Client).filter(
        models.Client.restaurant_id == restaurant_id
    ).all()
    
    result = []
    
    for client in clients:
        print(f"📋 Processing client: {client.id}")
        
        # Get last 2 messages for this client, ordered by timestamp DESC
        last_messages = db.query(models.ChatMessage).filter(
            models.ChatMessage.client_id == client.id,
            models.ChatMessage.restaurant_id == restaurant_id
        ).order_by(desc(models.ChatMessage.timestamp)).limit(2).all()
        
        print(f"   Found {len(last_messages)} recent messages")
        
        if not last_messages:
            continue  # Skip clients with no messages
        
        # Get AI enabled state from client preferences
        ai_enabled = True  # Default
        if client.preferences:
            ai_enabled = client.preferences.get("ai_enabled", True)
        
        # Process each of the last 2 messages
        for i, message in enumerate(last_messages):
            print(f"   Message {i+1}: [{message.sender_type}] {message.message[:30]}...")
            
            result.append({
                "client_id": str(message.client_id),
                "table_id": "",  # ChatMessage doesn't have table_id
                "message": message.message,
                "answer": "",  # Legacy field for compatibility
                "timestamp": message.timestamp,
                "ai_enabled": ai_enabled,
                "sender_type": message.sender_type
            })
    
    # Sort result by timestamp DESC to show most recent conversations first
    result.sort(key=lambda x: x["timestamp"], reverse=True)
    
    print(f"📋 Returning {len(result)} messages from {len(clients)} clients (up to 2 per client)")
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
    client = get_or_create_client(db, client_id, restaurant_id)
    print(f"✅ Ensured client exists: {client.id}")

    
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

    # ✅ MIGRATED: Store ai_enabled in Client.preferences instead of ChatLog
    # Convert string client_id to UUID for database query
    try:
        client_uuid = uuid.UUID(payload.client_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid client_id format")
    
    client = db.query(models.Client).filter(
        models.Client.id == client_uuid,
        models.Client.restaurant_id == payload.restaurant_id
    ).first()
    
    if not client:
        raise HTTPException(status_code=404, detail="Client not found")
    
    # Initialize preferences if None
    if client.preferences is None:
        client.preferences = {}
    
    # Update ai_enabled in preferences
    client.preferences["ai_enabled"] = payload.enabled
    
    # Mark the field as modified for SQLAlchemy to detect the change
    from sqlalchemy.orm.attributes import flag_modified
    flag_modified(client, "preferences")
    
    db.commit()
    
    return {"status": "ok", "enabled": payload.enabled}
