"""
Stub for mia_chat_service_hybrid - provides compatibility for RAG services
The actual implementation is in mia_chat_service_internal_tools_v5
"""
import os
import logging
from typing import Dict, Optional, List
from enum import Enum
from schemas.chat import ChatResponse

logger = logging.getLogger(__name__)

# MIA Backend URL
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

class QueryType(Enum):
    """Types of customer queries"""
    MENU = "menu"
    HOURS = "hours"
    LOCATION = "location"
    GREETING = "greeting"
    UNKNOWN = "unknown"

class HybridQueryClassifier:
    """Stub query classifier for compatibility"""
    @staticmethod
    def classify(message: str) -> QueryType:
        message_lower = message.lower()
        
        if any(word in message_lower for word in ['menu', 'food', 'dish', 'eat', 'pasta', 'pizza']):
            return QueryType.MENU
        elif any(word in message_lower for word in ['hours', 'open', 'close', 'time']):
            return QueryType.HOURS
        elif any(word in message_lower for word in ['where', 'location', 'address', 'find']):
            return QueryType.LOCATION
        elif any(word in message_lower for word in ['hello', 'hi', 'hey', 'good']):
            return QueryType.GREETING
        else:
            return QueryType.UNKNOWN

def get_maria_system_prompt(restaurant_name: str = "Bella Vista") -> str:
    """Get Maria's system prompt"""
    return f"""You are Maria, a warm and friendly AI assistant for {restaurant_name}. 
Be conversational and helpful while maintaining professionalism."""

def get_hybrid_parameters() -> Dict:
    """Get default MIA parameters"""
    return {
        "temperature": 0.7,
        "max_tokens": 512,
        "top_p": 0.9
    }

def get_mia_response_hybrid(prompt: str, restaurant_id: str, conversation_history: Optional[List] = None) -> str:
    """Stub for hybrid MIA response - delegates to v5"""
    # This is just a compatibility stub
    # The actual implementation should use mia_chat_service_internal_tools_v5
    return "Please use the internal tools v5 service for actual responses."

def detect_language(text: str) -> str:
    """Simple language detection"""
    # Very basic detection
    if any(word in text.lower() for word in ['bonjour', 'merci', 'oui', 'non']):
        return 'fr'
    elif any(word in text.lower() for word in ['hola', 'gracias', 'si', 'no']):
        return 'es'
    else:
        return 'en'

def get_persona_name() -> str:
    """Get the AI persona name"""
    return "Maria"

def mia_chat_service_hybrid(request, db):
    """Stub hybrid service - should not be used directly"""
    # Import v5 and use it
    from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5
    return mia_chat_service_internal_tools_v5(request, db)

def get_or_create_client(db, client_id: str, restaurant_id: str):
    """Get or create client - delegates to chat_service"""
    from services.chat_service import get_or_create_client as get_client
    return get_client(db, client_id, "", restaurant_id)