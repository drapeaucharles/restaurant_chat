"""
Configuration for Restaurant Backend with automatic fallback
Tries MIA first, falls back to OpenAI if unavailable
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
    AUTO = "auto"  # Automatically choose based on availability

# Chat provider configuration
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", ChatProvider.AUTO.value)

# MIA Configuration
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_MINER_URL = os.getenv("MIA_MINER_URL", "http://localhost:8000")  # Local miner instance

# OpenAI Configuration (fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

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
        logger.info("MIA backend is available - using MIA")
        USE_MIA_FOR_CHAT = True
    elif OPENAI_API_KEY:
        logger.info("MIA not available, falling back to OpenAI")
        USE_MIA_FOR_CHAT = False
    else:
        logger.warning("Neither MIA nor OpenAI available - using fallback responses")
        USE_MIA_FOR_CHAT = True  # Will use MIA service with fallbacks
else:
    USE_MIA_FOR_CHAT = CHAT_PROVIDER in [ChatProvider.MIA.value, ChatProvider.MIA_LOCAL.value]

USE_LOCAL_MIA_MINER = CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value

# Logging
ENABLE_CHAT_LOGGING = os.getenv("ENABLE_CHAT_LOGGING", "true").lower() == "true"

def get_chat_service():
    """
    Get the appropriate chat service based on configuration
    """
    if USE_MIA_FOR_CHAT:
        from services.mia_chat_service import mia_chat_service
        return mia_chat_service
    else:
        from services.chat_service import chat_service
        return chat_service

def get_chat_provider_info():
    """
    Get information about the current chat provider
    """
    if CHAT_PROVIDER == ChatProvider.AUTO.value:
        mia_available = check_mia_available()
        return {
            "provider": "Auto",
            "using": "MIA" if mia_available else "OpenAI",
            "mia_available": mia_available,
            "description": "Automatically choosing based on availability"
        }
    elif CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value:
        return {
            "provider": "MIA Local",
            "url": MIA_MINER_URL,
            "description": "Using local MIA miner instance"
        }
    elif CHAT_PROVIDER == ChatProvider.MIA.value:
        return {
            "provider": "MIA Backend",
            "url": MIA_BACKEND_URL,
            "description": "Using MIA distributed backend"
        }
    else:
        return {
            "provider": "OpenAI",
            "model": "gpt-4",
            "description": "Using OpenAI GPT-4"
        }

# Performance settings for MIA
MIA_MAX_TOKENS = int(os.getenv("MIA_MAX_TOKENS", "150"))
MIA_TIMEOUT = int(os.getenv("MIA_TIMEOUT", "30"))
MIA_RETRY_ATTEMPTS = int(os.getenv("MIA_RETRY_ATTEMPTS", "2"))