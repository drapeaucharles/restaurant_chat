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


@router.get("/logs/latest")
def get_latest_logs_grouped_by_client(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    if current_restaurant.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail="Access denied")

    # First, get subquery of latest message timestamps per client
    latest_subquery = (
        db.query(
            models.ChatLog.client_id,
            func.max(models.ChatLog.timestamp).label("latest_ts")
        )
        .filter(models.ChatLog.restaurant_id == restaurant_id)
        .group_by(models.ChatLog.client_id)
        .subquery()
    )

    # Join to the actual ChatLog table on both client_id and timestamp
    logs = (
        db.query(models.ChatLog)
        .join(
            latest_subquery,
            (models.ChatLog.client_id == latest_subquery.c.client_id) &
            (models.ChatLog.timestamp == latest_subquery.c.latest_ts)
        )
        .order_by(desc(models.ChatLog.timestamp))
        .all()
    )

    return [
        {
            "client_id": str(log.client_id),
            "table_id": log.table_id,
            "message": log.message,
            "answer": log.answer,
            "timestamp": log.timestamp,
            "ai_enabled": log.ai_enabled,  # ✅ Include AI status
            "sender_type": "client"  # ✅ Messages are always from client
        }
        for log in logs
    ]


@router.get("/logs/client")
def get_full_chat_history_for_client(
    restaurant_id: str,
    client_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    if current_restaurant.restaurant_id != restaurant_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Access denied")

    logs = db.query(models.ChatLog).filter(
        models.ChatLog.restaurant_id == restaurant_id,
        models.ChatLog.client_id == client_id
    ).order_by(models.ChatLog.timestamp).all()

    return [
        {
            "client_id": str(log.client_id),
            "table_id": log.table_id,
            "message": log.message,
            "answer": log.answer,
            "timestamp": log.timestamp,
            "ai_enabled": getattr(log, "ai_enabled", True),  # ✅ Include AI status with fallback
            "sender_type": "client",  # ✅ Messages are always from client
            "sender_type_answer": "ai" if getattr(log, "ai_enabled", True) else "restaurant"  # ✅ Answer type based on AI status
        }
        for log in logs
    ]


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
