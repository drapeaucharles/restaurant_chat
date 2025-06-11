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

router = APIRouter(prefix="/clients", tags=["clients"])


@router.post("/", response_model=ClientResponse)
def create_client(
    client_data: ClientCreateRequest,
    db: Session = Depends(get_db)
):
    """Create a new client."""
    # Check if restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == client_data.restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Create new client
    new_client = models.Client(
        restaurant_id=client_data.restaurant_id,
        name=client_data.name,
        email=client_data.email,
        preferences=client_data.preferences or {}
    )
    
    db.add(new_client)
    db.commit()
    db.refresh(new_client)
    
    return ClientResponse(
        id=new_client.id,
        restaurant_id=new_client.restaurant_id,
        name=new_client.name,
        email=new_client.email,
        first_seen=new_client.first_seen.isoformat(),
        last_seen=new_client.last_seen.isoformat() if new_client.last_seen else new_client.first_seen.isoformat(),
        preferences=new_client.preferences
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

