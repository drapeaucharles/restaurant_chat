"""
Configuration for Restaurant Backend
Allows switching between OpenAI and MIA chat services
"""
import os
from enum import Enum

class ChatProvider(Enum):
    OPENAI = "openai"
    MIA = "mia"
    MIA_LOCAL = "mia_local"

# Chat provider configuration
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", ChatProvider.MIA_LOCAL.value)

# MIA Configuration
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_MINER_URL = os.getenv("MIA_MINER_URL", "http://localhost:8000")  # Local miner instance

# OpenAI Configuration (fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Feature flags
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
    if CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value:
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