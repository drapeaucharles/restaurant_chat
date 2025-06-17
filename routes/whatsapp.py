"""
WhatsApp integration routes for FastAPI.
Handles incoming messages, outgoing messages, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import uuid

from auth import get_current_restaurant
from database import get_db
import models
from schemas.whatsapp import (
    WhatsAppIncomingMessage,
    WhatsAppOutgoingMessage, 
    WhatsAppSessionCreate,
    WhatsAppSessionResponse,
    WhatsAppSendResponse,
    WhatsAppWebhookResponse
)
from schemas.chat import ChatRequest, ChatResponse
from services.whatsapp_service import whatsapp_service
from services.chat_service import chat_service

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


@router.post("/incoming", response_model=WhatsAppWebhookResponse)
async def receive_whatsapp_message(
    message: WhatsAppIncomingMessage,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Receive incoming WhatsApp messages from open-wa webhook.
    Forwards messages to existing AI/staff logic via ChatService.
    """
    try:
        print(f"\n🔍 ===== WHATSAPP INCOMING MESSAGE =====")
        print(f"📱 From: {message.from_number}")
        print(f"💬 Message: '{message.message}'")
        print(f"🔗 Session ID: {message.session_id}")
        
        # Find restaurant by session ID
        restaurant = whatsapp_service.find_restaurant_by_session(message.session_id, db)
        if not restaurant:
            print(f"❌ No restaurant found for session: {message.session_id}")
            return WhatsAppWebhookResponse(
                success=False,
                error="Restaurant not found for this session"
            )
        
        print(f"✅ Restaurant found: {restaurant.restaurant_id}")
        
        # Generate consistent client ID from phone number
        client_id = whatsapp_service.generate_client_id_from_phone(message.from_number)
        print(f"👤 Generated client ID: {client_id}")
        
        # Create chat request (table_id=None for WhatsApp as specified)
        chat_request = ChatRequest(
            restaurant_id=restaurant.restaurant_id,
            client_id=uuid.UUID(client_id),
            message=message.message,
            sender_type='client'  # WhatsApp messages are always from clients
        )
        
        # Process message through existing chat service
        print(f"🤖 Processing through chat service...")
        chat_response = chat_service(chat_request, db)
        
        # If AI responded, send reply back to WhatsApp
        if chat_response.answer and chat_response.answer.strip():
            print(f"📤 Sending AI response back to WhatsApp...")
            
            # Send response back to WhatsApp in background
            background_tasks.add_task(
                send_whatsapp_reply,
                message.from_number,
                chat_response.answer,
                message.session_id
            )
            
            print(f"✅ AI response queued for sending")
        else:
            print(f"🔇 No AI response to send (empty or disabled)")
        
        print(f"===== END WHATSAPP INCOMING =====\n")
        
        return WhatsAppWebhookResponse(
            success=True,
            message="Message processed successfully"
        )
        
    except Exception as e:
        print(f"❌ Error processing WhatsApp message: {str(e)}")
        return WhatsAppWebhookResponse(
            success=False,
            error=f"Failed to process message: {str(e)}"
        )


@router.post("/send", response_model=WhatsAppSendResponse)
async def send_whatsapp_message(
    message: WhatsAppOutgoingMessage,
    db: Session = Depends(get_db)
):
    """
    Send a message via WhatsApp using open-wa.
    Takes to_number and message, sends POST to open-wa server.
    """
    try:
        print(f"\n📤 ===== SENDING WHATSAPP MESSAGE =====")
        print(f"📱 To: {message.to_number}")
        print(f"💬 Message: '{message.message}'")
        print(f"🔗 Session ID: {message.session_id}")
        
        # If no session_id provided, try to find one
        if not message.session_id:
            # For now, we'll require session_id to be provided
            # In the future, we could implement logic to find the appropriate session
            raise HTTPException(
                status_code=400,
                detail="session_id is required for sending messages"
            )
        
        # Send message via WhatsApp service
        result = await whatsapp_service.send_message(message)
        
        print(f"✅ Send result: success={result.success}")
        if result.error:
            print(f"❌ Send error: {result.error}")
        
        print(f"===== END SENDING WHATSAPP =====\n")
        
        return result
        
    except Exception as e:
        print(f"❌ Error sending WhatsApp message: {str(e)}")
        return WhatsAppSendResponse(
            success=False,
            error=f"Failed to send message: {str(e)}"
        )


@router.post("/restaurant/{restaurant_id}/connect", response_model=WhatsAppSessionResponse)
async def connect_restaurant_whatsapp(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """
    Connect a restaurant to WhatsApp by creating a session.
    Triggers session creation on open-wa side and returns QR code.
    """
    try:
        print(f"\n🔗 ===== CONNECTING RESTAURANT TO WHATSAPP =====")
        print(f"🏪 Restaurant ID: {restaurant_id}")
        print(f"🔐 Authenticated as: {current_restaurant.restaurant_id}")
        
        # Verify the authenticated restaurant matches the requested one
        if current_restaurant.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=403,
                detail="You can only connect WhatsApp for your own restaurant"
            )
        
        # Check if restaurant already has a WhatsApp session
        if current_restaurant.whatsapp_session_id:
            print(f"⚠️ Restaurant already has session: {current_restaurant.whatsapp_session_id}")
            
            # Check session status
            status = await whatsapp_service.get_session_status(current_restaurant.whatsapp_session_id)
            
            if status.get("status") == "connected":
                return WhatsAppSessionResponse(
                    session_id=current_restaurant.whatsapp_session_id,
                    status="already_connected",
                    message="Restaurant is already connected to WhatsApp"
                )
        
        # Create new session
        result = await whatsapp_service.create_session(restaurant_id, db)
        
        print(f"✅ Session creation result: {result.status}")
        print(f"===== END WHATSAPP CONNECTION =====\n")
        
        return result
        
    except HTTPException:
        raise
    except Exception as e:
        print(f"❌ Error connecting WhatsApp: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect WhatsApp: {str(e)}"
        )


async def send_whatsapp_reply(to_number: str, message: str, session_id: str):
    """
    Background task to send WhatsApp reply.
    Used to send AI responses back to WhatsApp users.
    """
    try:
        outgoing_message = WhatsAppOutgoingMessage(
            to_number=to_number,
            message=message,
            session_id=session_id
        )
        
        result = await whatsapp_service.send_message(outgoing_message)
        
        if result.success:
            print(f"✅ WhatsApp reply sent successfully to {to_number}")
        else:
            print(f"❌ Failed to send WhatsApp reply: {result.error}")
            
    except Exception as e:
        print(f"❌ Error in background WhatsApp reply: {str(e)}")


@router.get("/restaurant/{restaurant_id}/status")
async def get_whatsapp_status(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """
    Get WhatsApp connection status for a restaurant.
    """
    try:
        # Verify the authenticated restaurant matches the requested one
        if current_restaurant.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=403,
                detail="You can only check WhatsApp status for your own restaurant"
            )
        
        if not current_restaurant.whatsapp_session_id:
            return {
                "connected": False,
                "session_id": None,
                "phone_number": current_restaurant.whatsapp_number,
                "status": "not_connected"
            }
        
        # Get session status from open-wa
        status = await whatsapp_service.get_session_status(current_restaurant.whatsapp_session_id)
        
        return {
            "connected": status.get("status") == "connected",
            "session_id": current_restaurant.whatsapp_session_id,
            "phone_number": current_restaurant.whatsapp_number,
            "status": status.get("status", "unknown"),
            "details": status
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get WhatsApp status: {str(e)}"
        )

