"""
MIA Chat Service Improved - Alias for the fixed tools service
This provides backward compatibility for the routes expecting mia_chat_service_improved
"""

# Import the fixed service with tools support
from services.mia_chat_service_full_menu_with_tools_fixed import mia_chat_service

# The mia_chat_service function is already properly exported from the fixed module