"""
Enhanced configuration with improved chat service
"""
import os
import requests
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class ChatProvider(Enum):
    OPENAI = "openai"
    MIA = "mia"
    MIA_LOCAL = "mia_local"
    MIA_ENHANCED = "mia_enhanced"  # New enhanced version
    AUTO = "auto"

# Provider selection from environment
CHAT_PROVIDER = os.getenv("CHAT_PROVIDER", ChatProvider.MIA_ENHANCED.value)

# MIA Configuration
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_MINER_URL = os.getenv("MIA_MINER_URL", "http://localhost:8000")  # Local miner instance

# Redis configuration for caching
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Skip local MIA if it's not following instructions properly
SKIP_LOCAL_MIA = os.getenv("SKIP_LOCAL_MIA", "true")

# Check MIA availability
def check_mia_health():
    """Check if MIA backend is available"""
    try:
        response = requests.get(f"{MIA_BACKEND_URL}/api/health", timeout=2)
        return response.status_code == 200
    except:
        return False

# Auto-detect best provider
if CHAT_PROVIDER == ChatProvider.AUTO.value:
    # Check MIA availability
    if check_mia_health():
        USE_MIA_FOR_CHAT = True
        USE_ENHANCED_MIA = True
        logger.info("Auto-detected: Using enhanced MIA backend")
    else:
        USE_MIA_FOR_CHAT = False
        USE_ENHANCED_MIA = False
        logger.info("Auto-detected: MIA unavailable, will use OpenAI")
    
    # Force MIA in auto mode for now since we want to use it
    if os.getenv("FORCE_MIA_IN_AUTO", "true").lower() == "true":
        USE_MIA_FOR_CHAT = True
        USE_ENHANCED_MIA = True
else:
    # Manual provider selection
    USE_MIA_FOR_CHAT = CHAT_PROVIDER in [
        ChatProvider.MIA.value, 
        ChatProvider.MIA_LOCAL.value, 
        ChatProvider.MIA_ENHANCED.value
    ]
    USE_ENHANCED_MIA = CHAT_PROVIDER == ChatProvider.MIA_ENHANCED.value

USE_LOCAL_MIA_MINER = CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value and SKIP_LOCAL_MIA.lower() != "true"

# Import appropriate chat service
def get_chat_service():
    """Get the appropriate chat service based on configuration"""
    if not USE_MIA_FOR_CHAT:
        from services.chat_service import openai_chat_service
        logger.info("Using OpenAI chat service")
        return openai_chat_service
    elif USE_ENHANCED_MIA:
        from services.mia_chat_service_enhanced import mia_chat_service_enhanced
        logger.info("Using enhanced MIA chat service with caching and dynamic parameters")
        return mia_chat_service_enhanced
    else:
        from services.mia_chat_service import mia_chat_service
        logger.info("Using standard MIA chat service")
        return mia_chat_service

# Get provider info for logging
def get_provider_info():
    """Get information about the current chat provider"""
    if CHAT_PROVIDER == ChatProvider.AUTO.value:
        detected_provider = "Enhanced MIA" if USE_ENHANCED_MIA else ("MIA" if USE_MIA_FOR_CHAT else "OpenAI")
        return {
            "mode": "auto",
            "detected": detected_provider,
            "mia_available": check_mia_health()
        }
    elif CHAT_PROVIDER == ChatProvider.MIA_ENHANCED.value:
        return {
            "mode": "enhanced_mia",
            "url": MIA_BACKEND_URL,
            "features": [
                "Enhanced prompts with role-playing",
                "Redis-based caching",
                "Dynamic temperature adjustment",
                "Multi-language support",
                "Query type detection",
                "Conversation memory"
            ]
        }
    elif CHAT_PROVIDER == ChatProvider.MIA_LOCAL.value:
        return {
            "mode": "mia_local",
            "url": MIA_MINER_URL,
            "note": "Local miner (may have instruction-following issues)"
        }
    elif CHAT_PROVIDER == ChatProvider.MIA.value:
        return {
            "mode": "mia",
            "url": MIA_BACKEND_URL,
            "note": "Standard MIA backend"
        }
    else:
        return {
            "mode": "openai",
            "note": "Using OpenAI API"
        }

# OpenAI configuration (if needed as fallback)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Enhanced MIA settings
MIA_MAX_TOKENS = int(os.getenv("MIA_MAX_TOKENS", "400"))  # Increased from 150
MIA_TIMEOUT = int(os.getenv("MIA_TIMEOUT", "30"))
MIA_RETRY_ATTEMPTS = int(os.getenv("MIA_RETRY_ATTEMPTS", "2"))

# Cache settings
CACHE_ENABLED = os.getenv("CACHE_ENABLED", "true").lower() == "true"
CACHE_TTL_GENERAL = int(os.getenv("CACHE_TTL_GENERAL", "3600"))  # 1 hour
CACHE_TTL_GREETING = int(os.getenv("CACHE_TTL_GREETING", "86400"))  # 24 hours

# Enhanced features flags
ENABLE_QUERY_ANALYSIS = os.getenv("ENABLE_QUERY_ANALYSIS", "true").lower() == "true"
ENABLE_DYNAMIC_TEMPERATURE = os.getenv("ENABLE_DYNAMIC_TEMPERATURE", "true").lower() == "true"
ENABLE_CONVERSATION_MEMORY = os.getenv("ENABLE_CONVERSATION_MEMORY", "true").lower() == "true"

# Log configuration on startup
logger.info(f"Chat Provider Configuration: {get_provider_info()}")
logger.info(f"Enhanced Features: Query Analysis={ENABLE_QUERY_ANALYSIS}, Dynamic Temp={ENABLE_DYNAMIC_TEMPERATURE}, Memory={ENABLE_CONVERSATION_MEMORY}")
logger.info(f"Caching: Enabled={CACHE_ENABLED}, Redis={REDIS_HOST}:{REDIS_PORT}")