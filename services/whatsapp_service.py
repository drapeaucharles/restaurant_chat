"""
WhatsApp service for integrating with open-wa (wa-automate-nodejs)
Handles session management, message sending, and phone number mapping.
"""

import httpx
import os
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from fastapi import HTTPException
import models
from schemas.whatsapp import (
    WhatsAppIncomingMessage, 
    WhatsAppOutgoingMessage, 
    WhatsAppSessionCreate,
    WhatsAppSessionResponse,
    WhatsAppSendResponse
)


class WhatsAppService:
    """Service class for WhatsApp integration with open-wa"""
    
    def __init__(self):
        # Default open-wa server URL - can be configured via environment
        self.open_wa_url = os.getenv("OPEN_WA_URL", "http://localhost:8002")
        # Use the existing WHATSAPP_API_KEY from .env file
        self.whatsapp_api_key = os.getenv("WHATSAPP_API_KEY", "supersecretkey123")
        self.timeout = 30  # HTTP timeout in seconds
    
    async def create_session(self, restaurant_id: str, db: Session) -> WhatsAppSessionResponse:
        """
        Create a new WhatsApp session for a restaurant
        Triggers session creation on the open-wa side
        """
        try:
            print(f"\n🔍 ===== WHATSAPP CREATE SESSION DEBUG =====")
            print(f"🏪 Restaurant ID: {restaurant_id}")
            print(f"🔗 Open-WA URL: {self.open_wa_url}")
            print(f"🔑 API Key: {self.whatsapp_api_key[:10]}...")
            
            # Check if restaurant exists
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == restaurant_id
            ).first()
            
            if not restaurant:
                print(f"❌ Restaurant not found: {restaurant_id}")
                raise HTTPException(status_code=404, detail="Restaurant not found")
            
            print(f"✅ Restaurant found: {restaurant.restaurant_id}")
            
            # Generate session ID based on restaurant ID
            session_id = f"restaurant_{restaurant_id}"
            print(f"🆔 Generated session ID: {session_id}")
            
            # Prepare request data
            request_data = {
                "session_id": session_id,
                "webhook_url": f"{os.getenv('BACKEND_URL', 'http://localhost:8000')}/whatsapp/incoming"
            }
            print(f"📤 Request data: {request_data}")
            
            # Prepare headers with authentication
            headers = {
                "Authorization": f"Bearer {self.whatsapp_api_key}",
                "Content-Type": "application/json"
            }
            print(f"📋 Request headers: {headers}")
            
            # Call open-wa to create session
            print(f"🌐 Making POST request to: {self.open_wa_url}/session/create")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                try:
                    response = await client.post(
                        f"{self.open_wa_url}/session/create",
                        json=request_data,
                        headers=headers
                    )
                    
                    print(f"📊 Response status: {response.status_code}")
                    print(f"📄 Response headers: {dict(response.headers)}")
                    
                    # Try to get response text for debugging
                    try:
                        response_text = response.text
                        print(f"📝 Response text: {response_text}")
                    except Exception as e:
                        print(f"⚠️ Could not read response text: {str(e)}")
                        response_text = "Could not read response"
                    
                    if response.status_code == 200:
                        try:
                            data = response.json()
                            print(f"✅ Response JSON: {data}")
                            
                            # Update restaurant with session ID
                            restaurant.whatsapp_session_id = session_id
                            db.commit()
                            print(f"💾 Updated restaurant with session ID")
                            
                            return WhatsAppSessionResponse(
                                session_id=session_id,
                                qr_code=data.get("qr_code"),
                                status="created",
                                message="Session created successfully. Scan QR code to connect WhatsApp."
                            )
                        except Exception as json_error:
                            print(f"❌ JSON parsing error: {str(json_error)}")
                            import traceback
                            traceback.print_exc()
                            return WhatsAppSessionResponse(
                                session_id="",
                                status="error",
                                message=f"Invalid JSON response from WhatsApp service: {str(json_error)}"
                            )
                    else:
                        print(f"❌ HTTP error {response.status_code}: {response_text}")
                        return WhatsAppSessionResponse(
                            session_id="",
                            status="error",
                            message=f"WhatsApp service returned error {response.status_code}: {response_text}"
                        )
                        
                except httpx.ConnectError as e:
                    print(f"❌ Connection error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return WhatsAppSessionResponse(
                        session_id="",
                        status="error",
                        message=f"Could not connect to WhatsApp service at {self.open_wa_url}: {str(e)}"
                    )
                except httpx.TimeoutException as e:
                    print(f"❌ Timeout error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return WhatsAppSessionResponse(
                        session_id="",
                        status="error",
                        message=f"WhatsApp service request timed out after {self.timeout}s: {str(e)}"
                    )
                except httpx.RequestError as e:
                    print(f"❌ Request error: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return WhatsAppSessionResponse(
                        session_id="",
                        status="error",
                        message=f"Request error when calling WhatsApp service: {str(e)}"
                    )
                    
        except httpx.RequestError as e:
            # Handle connection errors gracefully
            print(f"❌ Connection error in create_session: {str(e)}")
            import traceback
            traceback.print_exc()
            return WhatsAppSessionResponse(
                session_id="",
                status="error",
                message=f"Could not connect to WhatsApp service: {str(e)}"
            )
        except HTTPException as e:
            print(f"❌ HTTP Exception: {e.detail}")
            import traceback
            traceback.print_exc()
            raise
        except Exception as e:
            print(f"❌ Unexpected error in create_session: {str(e)}")
            import traceback
            traceback.print_exc()
            return WhatsAppSessionResponse(
                session_id="",
                status="error",
                message=f"Unexpected error during session creation: {str(e)}"
            )
        finally:
            print(f"===== END WHATSAPP CREATE SESSION DEBUG =====\n")
    
    async def send_message(self, message: WhatsAppOutgoingMessage) -> WhatsAppSendResponse:
        """
        Send a message via WhatsApp using open-wa
        """
        try:
            print(f"\n📤 ===== WHATSAPP SEND MESSAGE DEBUG =====")
            print(f"📱 To: {message.to_number}")
            print(f"💬 Message: {message.message[:100]}...")
            print(f"🆔 Session ID: {message.session_id}")
            
            headers = {
                "Authorization": f"Bearer {self.whatsapp_api_key}",
                "Content-Type": "application/json"
            }
            
            request_data = {
                "to": message.to_number,
                "message": message.message,
                "session_id": message.session_id
            }
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    f"{self.open_wa_url}/message/send",
                    json=request_data,
                    headers=headers
                )
                
                print(f"📊 Send response status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"✅ Send successful: {data}")
                        return WhatsAppSendResponse(
                            success=True,
                            message_id=data.get("message_id")
                        )
                    except Exception as e:
                        print(f"❌ JSON parsing error in send: {str(e)}")
                        import traceback
                        traceback.print_exc()
                        return WhatsAppSendResponse(
                            success=False,
                            error=f"Invalid JSON response: {str(e)}"
                        )
                else:
                    error_text = response.text
                    print(f"❌ Send failed: {error_text}")
                    return WhatsAppSendResponse(
                        success=False,
                        error=f"Failed to send message (HTTP {response.status_code}): {error_text}"
                    )
                    
        except httpx.RequestError as e:
            print(f"❌ Send request error: {str(e)}")
            import traceback
            traceback.print_exc()
            return WhatsAppSendResponse(
                success=False,
                error=f"Could not connect to WhatsApp service: {str(e)}"
            )
        except Exception as e:
            print(f"❌ Send unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return WhatsAppSendResponse(
                success=False,
                error=f"Message sending failed: {str(e)}"
            )
        finally:
            print(f"===== END WHATSAPP SEND MESSAGE DEBUG =====\n")
    
    def find_restaurant_by_phone(self, phone_number: str, db: Session) -> Optional[models.Restaurant]:
        """
        Find restaurant by WhatsApp phone number
        """
        return db.query(models.Restaurant).filter(
            models.Restaurant.whatsapp_number == phone_number
        ).first()
    
    def find_restaurant_by_session(self, session_id: str, db: Session) -> Optional[models.Restaurant]:
        """
        Find restaurant by WhatsApp session ID
        """
        return db.query(models.Restaurant).filter(
            models.Restaurant.whatsapp_session_id == session_id
        ).first()
    
    def generate_client_id_from_phone(self, phone_number: str) -> str:
        """
        Generate a consistent client ID from phone number
        This ensures the same phone number always gets the same client ID
        """
        import hashlib
        import uuid
        
        # Create a deterministic UUID from phone number
        namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Standard namespace UUID
        client_uuid = uuid.uuid5(namespace, phone_number)
        return str(client_uuid)
    
    def get_phone_number_for_client(self, client_id: str, db: Session) -> Optional[str]:
        """
        Get the phone number for a client by looking up the stored mapping
        """
        try:
            print(f"🔍 Looking up phone number for client: {client_id}")
            
            # Query the phone mapping table
            phone_mapping = db.query(models.ClientPhoneMapping).filter(
                models.ClientPhoneMapping.client_id == client_id
            ).first()
            
            if phone_mapping:
                print(f"✅ Found phone number: {phone_mapping.phone_number}")
                return phone_mapping.phone_number
            else:
                print(f"❌ No phone mapping found for client {client_id}")
                return None
            
        except Exception as e:
            print(f"❌ Error looking up phone number: {str(e)}")
            return None
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """
        Get the status of a WhatsApp session
        """
        try:
            print(f"\n🔍 ===== WHATSAPP GET SESSION STATUS =====")
            print(f"🆔 Session ID: {session_id}")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.open_wa_url}/session/{session_id}/status")
                
                print(f"📊 Status response: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Status data: {data}")
                    return data
                else:
                    print(f"❌ Status error: {response.text}")
                    return {"status": "error", "message": "Session not found"}
                    
        except httpx.RequestError as e:
            print(f"❌ Status request error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": "WhatsApp service unavailable"}
        except Exception as e:
            print(f"❌ Status unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {"status": "error", "message": str(e)}
        finally:
            print(f"===== END WHATSAPP GET SESSION STATUS =====\n")


# Global instance
whatsapp_service = WhatsAppService()

