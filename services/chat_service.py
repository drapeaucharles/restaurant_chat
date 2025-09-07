"""
Chat Service - Alias for the main MIA chat service
This provides backward compatibility for routes expecting chat_service
"""

# Import the main service
from services.mia_chat_service import mia_chat_service as chat_service
from services.mia_chat_service import get_or_create_client

# Export the functions with expected names
__all__ = ['chat_service', 'get_or_create_client']