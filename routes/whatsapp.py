"""
WhatsApp integration routes for FastAPI.
Handles incoming messages, outgoing messages, and session management.
"""

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
import uuid
import httpx

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
        
        # ✅ SAVE CUSTOMER MESSAGE TO DATABASE FIRST
        print(f"💾 Saving customer WhatsApp message to database...")
        customer_message = models.ChatMessage(
            restaurant_id=restaurant.restaurant_id,
            client_id=uuid.UUID(client_id),
            sender_type="client",
            message=message.message
        )
        db.add(customer_message)
        db.commit()
        db.refresh(customer_message)
        print(f"✅ Customer message saved to ChatMessage table with ID: {customer_message.id}")
        
        # ✅ STORE PHONE NUMBER MAPPING FOR FUTURE STAFF REPLIES
        print(f"📞 Storing phone number mapping for client...")
        try:
            # Check if mapping already exists
            existing_mapping = db.query(models.ClientPhoneMapping).filter(
                models.ClientPhoneMapping.client_id == uuid.UUID(client_id),
                models.ClientPhoneMapping.restaurant_id == restaurant.restaurant_id
            ).first()
            
            if existing_mapping:
                # Update existing mapping
                existing_mapping.phone_number = message.from_number
                existing_mapping.updated_at = func.now()
                print(f"✅ Updated existing phone mapping for client {client_id}")
            else:
                # Create new mapping
                phone_mapping = models.ClientPhoneMapping(
                    client_id=uuid.UUID(client_id),
                    phone_number=message.from_number,
                    restaurant_id=restaurant.restaurant_id
                )
                db.add(phone_mapping)
                print(f"✅ Created new phone mapping for client {client_id}")
            
            db.commit()
            print(f"📞 Phone mapping stored: {client_id} -> {message.from_number}")
            
        except Exception as e:
            print(f"❌ Error storing phone mapping: {str(e)}")
            # Don't fail the whole process if phone mapping fails
            db.rollback()
        
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


@router.post("/session/{session_id}/start", response_model=WhatsAppSessionResponse)
async def start_whatsapp_session(
    session_id: str,
    db: Session = Depends(get_db)
):
    """
    Start a WhatsApp session and generate QR code.
    This endpoint forwards the request to the Node.js WhatsApp service.
    """
    try:
        print(f"\n🚀 ===== STARTING WHATSAPP SESSION =====")
        print(f"🔗 Session ID: {session_id}")
        
        # Extract restaurant_id from session_id (assuming format: restaurant_RestaurantName)
        restaurant_id = session_id.replace('restaurant_', '') if session_id.startswith('restaurant_') else session_id
        
        # Find the restaurant in database
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == restaurant_id
        ).first()
        
        if not restaurant:
            print(f"❌ Restaurant not found: {restaurant_id}")
            return WhatsAppSessionResponse(
                session_id=session_id,
                status="error",
                message=f"Restaurant {restaurant_id} not found"
            )
        
        # Forward request to Node.js WhatsApp service
        async with httpx.AsyncClient(timeout=60) as client:
            response = await client.post(
                f"{whatsapp_service.open_wa_url}/session/{session_id}/start",
                headers={
                    "Content-Type": "application/json",
                    "x-api-key": whatsapp_service.whatsapp_api_key
                },
                json={"force_new": False}
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Session started successfully")
                
                # Update database with session ID if connection was successful
                if data.get("status") in ["qr_ready", "connected"]:
                    restaurant.whatsapp_session_id = session_id
                    db.commit()
                    print(f"✅ Updated database: {restaurant_id} -> session_id: {session_id}")
                
                return WhatsAppSessionResponse(
                    session_id=session_id,
                    status=data.get("status", "qr_ready"),
                    message=data.get("message", "Session started successfully"),
                    qr_code=data.get("qr_code")
                )
            else:
                error_text = response.text
                print(f"❌ Session start failed: {error_text}")
                return WhatsAppSessionResponse(
                    session_id=session_id,
                    status="error",
                    message=f"Failed to start session: {error_text}"
                )
                
    except Exception as e:
        print(f"❌ Error starting WhatsApp session: {str(e)}")
        return WhatsAppSessionResponse(
            session_id=session_id,
            status="error",
            message=f"Failed to start session: {str(e)}"
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
            print(f"❌ Authentication mismatch: {current_restaurant.restaurant_id} != {restaurant_id}")
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
                print(f"✅ Session already connected")
                return WhatsAppSessionResponse(
                    session_id=current_restaurant.whatsapp_session_id,
                    status="already_connected",
                    message="Restaurant is already connected to WhatsApp"
                )
        
        # Create new session
        print(f"🔄 Creating new WhatsApp session...")
        result = await whatsapp_service.create_session(restaurant_id, db)
        
        print(f"✅ Session creation result: {result.status}")
        if result.status == "error":
            print(f"❌ Session creation failed: {result.message}")
        
        print(f"===== END WHATSAPP CONNECTION =====\n")
        
        return result
        
    except HTTPException as e:
        print(f"❌ HTTP Exception in connect_restaurant_whatsapp: {e.detail}")
        import traceback
        traceback.print_exc()
        raise
    except Exception as e:
        print(f"❌ Unexpected error connecting WhatsApp: {str(e)}")
        import traceback
        traceback.print_exc()
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


@router.get("/restaurant/{restaurant_id}/qr")
async def get_whatsapp_qr(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """
    Get QR code for WhatsApp session.
    """
    try:
        # Verify the authenticated restaurant matches the requested one
        if current_restaurant.restaurant_id != restaurant_id:
            raise HTTPException(
                status_code=403,
                detail="You can only get QR code for your own restaurant"
            )
        
        if not current_restaurant.whatsapp_session_id:
            raise HTTPException(
                status_code=404,
                detail="No WhatsApp session found. Please connect first."
            )
        
        # Get QR code from WhatsApp service
        session_id = current_restaurant.whatsapp_session_id
        
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.get(
                f"{whatsapp_service.open_wa_url}/session/{session_id}/qr",
                headers={"x-api-key": whatsapp_service.whatsapp_api_key}
            )
            
            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "qr_code": data.get("qr_code"),
                    "session_id": session_id,
                    "status": data.get("status", "qr_ready")
                }
            else:
                return {
                    "success": False,
                    "error": f"Failed to get QR code: {response.text}",
                    "session_id": session_id
                }
                
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get QR code: {str(e)}"
        )


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

