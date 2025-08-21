"""
Universal model imports with backward compatibility
Use this instead of importing models directly
"""

# Try to import universal models first
try:
    from models_universal import (
        Business, Product, Client, ChatMessage,
        # Aliases for backward compatibility
        Restaurant, MenuItem
    )
    UNIVERSAL_MODELS = True
except ImportError:
    # Fall back to original models
    from models import (
        Restaurant, Client, ChatMessage
    )
    # Create aliases
    Business = Restaurant
    MenuItem = None  # Not available in old models
    Product = None
    UNIVERSAL_MODELS = False

# For code that uses models.Restaurant, models.Client, etc.
class models:
    Restaurant = Business  # Maps to Business in universal system
    Business = Business
    Client = Client
    ChatMessage = ChatMessage
    
    # Only available in universal system
    if UNIVERSAL_MODELS:
        Product = Product
        MenuItem = MenuItem