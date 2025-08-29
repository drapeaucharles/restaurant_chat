"""
Route modules initialization with MIA support.
"""
import os

# Import configuration to determine which chat module to use
try:
    from config import USE_MIA_FOR_CHAT
    config_available = True
except ImportError:
    config_available = False
    USE_MIA_FOR_CHAT = False

# Check for enhanced chat flag
USE_ENHANCED_CHAT = os.getenv("USE_ENHANCED_CHAT", "false").lower() == "true"

# Import other routes
from . import auth, restaurant, clients, chats

# Always use chat_dynamic for the dynamic RAG system
from . import chat_dynamic as chat
print("🤖 Restaurant using DYNAMIC RAG system with restaurant-specific modes")

__all__ = ["auth", "restaurant", "chat", "clients", "chats"]