"""
Route modules initialization with MIA support.
"""

# Import configuration to determine which chat module to use
try:
    from config import USE_MIA_FOR_CHAT
    config_available = True
except ImportError:
    config_available = False
    USE_MIA_FOR_CHAT = False

# Import other routes
from . import auth, restaurant, clients, chats

# Conditional import for chat based on configuration
if config_available and USE_MIA_FOR_CHAT:
    from . import chat_mia as chat
    print("🤖 Restaurant using MIA for chat responses")
else:
    from . import chat
    print("🤖 Restaurant using OpenAI for chat responses")

__all__ = ["auth", "restaurant", "chat", "clients", "chats"]