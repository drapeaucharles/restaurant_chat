"""
Chat Service - Alias for the main MIA chat service
This provides backward compatibility for routes expecting chat_service
"""

# Import the main service
from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5 as chat_service

# Define get_or_create_client function here since it's not in v5
from sqlalchemy.orm import Session
import models
import uuid

def get_or_create_client(db: Session, client_id: uuid.UUID, restaurant_id: str):
    """Get or create a client"""
    # First check if client exists globally (client IDs are unique across all restaurants)
    client = db.query(models.Client).filter_by(id=client_id).first()
    
    if not client:
        # Client doesn't exist at all, create new one
        client = models.Client(
            id=client_id,
            restaurant_id=restaurant_id
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    else:
        # Client exists but might be for different restaurant
        # Update the restaurant_id to current one (clients can chat with multiple restaurants)
        if client.restaurant_id != restaurant_id:
            client.restaurant_id = restaurant_id
            db.commit()
            db.refresh(client)
    
    return client

# Export the functions with expected names
__all__ = ['chat_service', 'get_or_create_client']