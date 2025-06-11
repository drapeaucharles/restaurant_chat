"""
Chat management routes and endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid

from database import get_db
import models
from schemas.chat import ChatMessageCreate, ChatMessageResponse

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("/", response_model=ChatMessageResponse)
def create_chat_message(
    message_data: ChatMessageCreate,
    db: Session = Depends(get_db)
):
    """Store a new chat message."""
    # Verify restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == message_data.restaurant_id
    ).first()

    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")

    # Check if client exists
    client = db.query(models.Client).filter(
        models.Client.id == message_data.client_id
    ).first()

    # ✅ Auto-create the client if not found
    if not client:
        client = models.Client(
            id=message_data.client_id,
            restaurant_id=message_data.restaurant_id
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    # Verify client belongs to the restaurant
    if client.restaurant_id != message_data.restaurant_id:
        raise HTTPException(status_code=403, detail="Client does not belong to this restaurant")

    # Create new chat message
    new_message = models.ChatMessage(
        restaurant_id=message_data.restaurant_id,
        client_id=message_data.client_id,
        sender_type=message_data.sender_type,
        message=message_data.message
    )

    db.add(new_message)
    db.commit()
    db.refresh(new_message)

    return ChatMessageResponse(
        id=new_message.id,
        restaurant_id=new_message.restaurant_id,
        client_id=new_message.client_id,
        sender_type=new_message.sender_type,
        message=new_message.message,
        timestamp=new_message.timestamp
    )


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
