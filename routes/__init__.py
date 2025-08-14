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

# Conditional import for chat based on configuration
if USE_ENHANCED_CHAT:
    from . import chat_enhanced as chat
    print("🤖 Restaurant using ENHANCED MIA with caching and dynamic parameters")
elif config_available and USE_MIA_FOR_CHAT:
    from . import chat_mia as chat
    print("🤖 Restaurant using MIA for chat responses")
else:
    from . import chat
    print("🤖 Restaurant using OpenAI for chat responses")

__all__ = ["auth", "restaurant", "chat", "clients", "chats"]