from pydantic import BaseModel
from typing import Optional, Dict, Any
import uuid


class WhatsAppIncomingMessage(BaseModel):
    """Schema for incoming WhatsApp messages from open-wa webhook"""
    from_number: str  # Phone number that sent the message
    message: str  # Message content
    session_id: str  # Session ID from open-wa
    message_id: Optional[str] = None  # WhatsApp message ID
    timestamp: Optional[str] = None  # Message timestamp
    chat_id: Optional[str] = None  # WhatsApp chat ID
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata from open-wa


class WhatsAppOutgoingMessage(BaseModel):
    """Schema for outgoing WhatsApp messages to open-wa"""
    to_number: str  # Phone number to send message to
    message: str  # Message content
    session_id: Optional[str] = None  # Session ID (optional, can be inferred)


class WhatsAppSessionCreate(BaseModel):
    """Schema for creating a new WhatsApp session"""
    restaurant_id: str  # Restaurant ID to associate with session
    session_name: Optional[str] = None  # Optional session name


class WhatsAppSessionResponse(BaseModel):
    """Schema for WhatsApp session creation response"""
    session_id: str  # Created session ID
    qr_code: Optional[str] = None  # Base64 QR code or URL
    status: str  # Session status (e.g., "created", "connecting", "connected")
    message: str  # Status message


class WhatsAppSendResponse(BaseModel):
    """Schema for WhatsApp send message response"""
    success: bool
    message_id: Optional[str] = None
    error: Optional[str] = None


class WhatsAppWebhookResponse(BaseModel):
    """Schema for webhook response to open-wa"""
    success: bool
    message: Optional[str] = None
    error: Optional[str] = None

