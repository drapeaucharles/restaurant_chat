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

def get_or_create_client(db: Session, client_id: str, restaurant_id: str):
    """Get or create a client"""
    client = db.query(models.Client).filter_by(
        id=client_id,
        restaurant_id=restaurant_id
    ).first()
    
    if not client:
        client = models.Client(
            id=client_id,
            restaurant_id=restaurant_id,
            device_info={}
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    
    return client

# Export the functions with expected names
__all__ = ['chat_service', 'get_or_create_client']