"""
Simple Test Visa Chat Service
Minimal implementation to test if basic AI routing works
"""

import logging
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

def simple_test_visa_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Simple test visa service to verify routing works"""
    
    logger.info(f"🎯 SIMPLE VISA TEST SERVICE CALLED for {req.restaurant_id}")
    
    try:
        # Simple hardcoded conversational response for testing
        if "hello" in req.message.lower() or "hi" in req.message.lower():
            answer = "Hi there! I'm Maya from GSI Bali Agency. I'd love to help you with your Indonesia visa! What brings you to Indonesia? 🇮🇩"
        elif "american" in req.message.lower():
            answer = "Awesome! You're American - that's great! For US citizens, we have some fantastic visa options. Are you thinking vacation, business, or maybe something else?"
        elif "canadian" in req.message.lower():
            answer = "Perfect! Canadian travelers love Indonesia! Based on your 3-week tourism plan, I'd recommend our Tourist Visa (B211A) - it's perfect for your trip and super easy to get!"
        elif "business" in req.message.lower():
            answer = "Business meetings in Jakarta - how exciting! For business purposes, you'll want our Business Visit Visa (B211B). Where are you from? That helps me give you the exact requirements."
        elif "visa" in req.message.lower():
            answer = "I'd be happy to help you find the perfect Indonesia visa! Tell me a bit about your plans - where are you from and what's bringing you to Indonesia?"
        else:
            answer = f"Thanks for reaching out! I'm Maya, your friendly visa consultant at GSI Bali Agency. I see you said: '{req.message}' - I'd love to help you with your Indonesia visa needs! What can I tell you about our visa services?"
        
        logger.info(f"✅ Simple visa service returning response: {answer[:50]}...")
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"❌ Error in simple visa service: {e}")
        return ChatResponse(answer="I'm Maya from GSI Bali Agency! I'm here to help with your Indonesia visa, but I'm having a small technical hiccup. Could you try asking again?")
