"""
Client management routes and endpoints.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from auth import get_current_restaurant
from database import get_db
import models
from schemas.client import ClientCreateRequest, ClientResponse
from services.chat_service import get_or_create_client  # Add this import

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientResponse)
def create_client(
    client_data: ClientCreateRequest,
    db: Session = Depends(get_db)
):
    """Create or get existing client."""
    # Check if restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == client_data.restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Use shared logic to avoid duplication
    client = get_or_create_client(db, client_data.id, client_data.restaurant_id)
    
    # Update optional fields if provided
    if client_data.name:
        client.name = client_data.name
    if client_data.email:
        client.email = client_data.email
    if client_data.preferences:
        client.preferences = client_data.preferences
    
    db.commit()
    db.refresh(client)

    return ClientResponse(
        id=client.id,
        restaurant_id=client.restaurant_id,
        name=client.name,
        email=client.email,
        first_seen=client.first_seen.isoformat(),
        last_seen=client.last_seen.isoformat() if client.last_seen else client.first_seen.isoformat(),
        preferences=client.preferences
    )


@router.get("/", response_model=List[ClientResponse])
def get_clients(
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """Get all clients for the current restaurant (protected endpoint)."""
    clients = db.query(models.Client).filter(
        models.Client.restaurant_id == current_restaurant.restaurant_id
    ).all()
    
    return [
        ClientResponse(
            id=client.id,
            restaurant_id=client.restaurant_id,
            name=client.name,
            email=client.email,
            first_seen=client.first_seen.isoformat(),
            last_seen=client.last_seen.isoformat() if client.last_seen else client.first_seen.isoformat(),
            preferences=client.preferences
        )
        for client in clients
    ]

