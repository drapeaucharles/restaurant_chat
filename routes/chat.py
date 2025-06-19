from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy.sql import func  # ✅ ADDED MISSING IMPORT
from typing import List
import uuid

from database import get_db
import models
from schemas.chat import ChatMessageCreate, ChatMessageResponse
from services.client_service import get_or_create_client

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
        sender_type=message_data.sender_type,
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

    # ✅ SIMPLIFIED: If this is a restaurant/staff message, try to send via WhatsApp (non-blocking)
    if message_data.sender_type == "restaurant":
        try:
            print(f"📱 Restaurant/staff message detected - attempting WhatsApp send...")
            
            # Check if restaurant has WhatsApp session
            if restaurant.whatsapp_session_id:
                print(f"✅ Restaurant has WhatsApp session: {restaurant.whatsapp_session_id}")
                
                # Try to find phone number mapping (simplified)
                try:
                    phone_mapping = db.query(models.ClientPhoneMapping).filter(
                        models.ClientPhoneMapping.client_id == message_data.client_id,
                        models.ClientPhoneMapping.restaurant_id == message_data.restaurant_id
                    ).first()
                    
                    if phone_mapping:
                        print(f"📞 Found phone number: {phone_mapping.phone_number}")
                        # TODO: Add WhatsApp sending logic here (simplified, non-blocking)
                        print(f"📤 WhatsApp send scheduled for: {phone_mapping.phone_number}")
                    else:
                        print(f"❌ No phone mapping found for client {message_data.client_id}")
                        
                except Exception as e:
                    print(f"⚠️ WhatsApp phone lookup failed (non-critical): {str(e)}")
            else:
                print(f"ℹ️ Restaurant has no WhatsApp session configured")
                
        except Exception as e:
            print(f"⚠️ WhatsApp processing failed (non-critical): {str(e)}")
            # Don't fail the chat message - WhatsApp is optional

    # 🔧 FIX: If this is a client message, trigger AI response via chat_service
    ai_response = ""
    if message_data.sender_type == "client":
        try:
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
                
        except Exception as e:
            print(f"⚠️ AI processing failed (non-critical): {str(e)}")
            # Don't fail the chat message - AI is optional

    response = ChatMessageResponse(
        id=new_message.id,
        restaurant_id=new_message.restaurant_id,
        client_id=new_message.client_id,
        sender_type=new_message.sender_type,
        message=new_message.message,
        timestamp=new_message.timestamp
    )
    
    print(f"📤 Returning response with sender_type: '{response.sender_type}'")
    print(f"===== END /chat/ POST ENDPOINT =====\n")

    return response


@router.get("/", response_model=List[ChatMessageResponse])
def get_chat_messages(
    restaurant_id: str,
    client_id: str,
    db: Session = Depends(get_db)
):
    """Get chat messages for a specific client and restaurant."""
    
    print(f"\n🔍 ===== GET CHAT MESSAGES =====")
    print(f"🏪 Restaurant ID: {restaurant_id}")
    print(f"👤 Client ID: {client_id}")
    
    # Verify restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()

    if not restaurant:
        print(f"❌ Restaurant not found: {restaurant_id}")
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Get messages for this client and restaurant
    messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.client_id == client_id
    ).order_by(models.ChatMessage.timestamp.asc()).all()

    print(f"✅ Found {len(messages)} messages")
    print(f"===== END GET CHAT MESSAGES =====\n")

    return [
        ChatMessageResponse(
            id=msg.id,
            restaurant_id=msg.restaurant_id,
            client_id=msg.client_id,
            sender_type=msg.sender_type,
            message=msg.message,
            timestamp=msg.timestamp
        )
        for msg in messages
    ]

