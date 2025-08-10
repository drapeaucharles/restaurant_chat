"""
Configuration for Restaurant Backend with improved MIA chat service
"""
import os
from enum import Enum
import logging
import requests

logger = logging.getLogger(__name__)

class ChatProvider(Enum):
    OPENAI = "openai"
    MIA = "mia"
    MIA_LOCAL = "mia_local"
    MIA_IMPROVED = "mia_improved"  # New improved version
    AUTO = "auto"  # Automatically choose based on availability

# Chat provider configuration - default to improved version
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", ChatProvider.MIA_IMPROVED.value)

# MIA Configuration
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_MINER_URL = os.getenv("MIA_MINER_URL", "http://localhost:8000")  # Local miner instance

# OpenAI Configuration (fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Skip local MIA by default (due to instruction-following issues)
SKIP_LOCAL_MIA = os.getenv("SKIP_LOCAL_MIA", "true")

# Check MIA availability
def check_mia_available():
    """Check if MIA backend is available and has the restaurant API"""
    try:
        response = requests.get(f"{MIA_BACKEND_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False

# Determine actual provider to use
if CHAT_PROVIDER == ChatProvider.AUTO.value:
    if check_mia_available():
        logger.info("MIA backend is available - using improved MIA service")
        USE_MIA_FOR_CHAT = True
        USE_IMPROVED_MIA = True
    elif OPENAI_API_KEY:
        logger.info("MIA not available, falling back to OpenAI")
        USE_MIA_FOR_CHAT = False
        USE_IMPROVED_MIA = False
    else:
        logger.warning("Neither MIA nor OpenAI available - using fallback responses")
        USE_MIA_FOR_CHAT = True  # Will use MIA service with fallbacks
        USE_IMPROVED_MIA = True
else:
    USE_MIA_FOR_CHAT = CHAT_PROVIDER in [ChatProvider.MIA.value, ChatProvider.MIA_LOCAL.value, ChatProvider.MIA_IMPROVED.value]
    USE_IMPROVED_MIA = CHAT_PROVIDER == ChatProvider.MIA_IMPROVED.value

USE_LOCAL_MIA_MINER = CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value and SKIP_LOCAL_MIA.lower() != "true"

# Logging
ENABLE_CHAT_LOGGING = os.getenv("ENABLE_CHAT_LOGGING", "true").lower() == "true"

def get_chat_service():
    """
    Get the appropriate chat service based on configuration
    """
    if USE_IMPROVED_MIA:
        from services.mia_chat_service_improved import mia_chat_service
        logger.info("Using improved MIA chat service")
        return mia_chat_service
    elif USE_MIA_FOR_CHAT:
        from services.mia_chat_service import mia_chat_service
        logger.info("Using standard MIA chat service")
        return mia_chat_service
    else:
        from services.chat_service import chat_service
        logger.info("Using OpenAI chat service")
        return chat_service

def get_chat_provider_info():
    """
    Get information about the current chat provider
    """
    if CHAT_PROVIDER == ChatProvider.AUTO.value:
        mia_available = check_mia_available()
        return {
            "provider": "Auto",
            "using": "MIA Improved" if mia_available else "OpenAI",
            "mia_available": mia_available,
            "improved_version": True,
            "description": "Automatically choosing based on availability (using improved AI responses)"
        }
    elif CHAT_PROVIDER == ChatProvider.MIA_IMPROVED.value:
        return {
            "provider": "MIA Improved",
            "url": MIA_BACKEND_URL,
            "improved_version": True,
            "features": [
                "Natural conversational responses",
                "Better context understanding",
                "Dynamic temperature adjustment",
                "Conversation history awareness",
                "Enhanced menu presentation"
            ],
            "description": "Using improved MIA backend with natural language processing"
        }
    elif CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value:
        return {
            "provider": "MIA Local",
            "url": MIA_MINER_URL,
            "skip_local": SKIP_LOCAL_MIA,
            "description": "Using local MIA miner instance" if not SKIP_LOCAL_MIA else "Configured for local but skipping due to issues"
        }
    elif CHAT_PROVIDER == ChatProvider.MIA.value:
        return {
            "provider": "MIA Backend",
            "url": MIA_BACKEND_URL,
            "description": "Using standard MIA distributed backend"
        }
    else:
        return {
            "provider": "OpenAI",
            "model": "gpt-4",
            "description": "Using OpenAI GPT-4"
        }

# Performance settings for MIA - increased for better responses
MIA_MAX_TOKENS = int(os.getenv("MIA_MAX_TOKENS", "400"))  # Increased from 150
MIA_TIMEOUT = int(os.getenv("MIA_TIMEOUT", "30"))

# Response enhancement settings
ENABLE_RESPONSE_ENHANCEMENT = os.getenv("ENABLE_RESPONSE_ENHANCEMENT", "true").lower() == "true"
CONVERSATION_HISTORY_HOURS = int(os.getenv("CONVERSATION_HISTORY_HOURS", "2"))
CONVERSATION_HISTORY_LIMIT = int(os.getenv("CONVERSATION_HISTORY_LIMIT", "10"))