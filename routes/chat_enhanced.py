"""
Enhanced chat endpoint with improved AI service
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from datetime import datetime
from services.mia_chat_service_enhanced_simple import mia_chat_service_enhanced_simple, get_or_create_client
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Use the simplified enhanced service
chat_service = mia_chat_service_enhanced_simple

@router.post("/", response_model=ChatResponse)
async def chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Enhanced chat endpoint with:
    - Query type detection
    - Dynamic temperature adjustment
    - Redis caching
    - Multi-language support
    - Better prompts
    """
    try:
        logger.info(f"Enhanced chat request from client {req.client_id} to restaurant {req.restaurant_id}")
        
        # Create client message
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type=req.sender_type,
            message=req.message
        )
        db.add(new_message)
        db.commit()
        
        # Get or create client
        get_or_create_client(db, req.client_id, req.restaurant_id)
        
        # Get AI response using enhanced service
        response = chat_service(req, db)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in enhanced chat endpoint: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/provider")
async def get_provider_info():
    """Get information about the current chat provider and features"""
    return {
        "provider": "mia_enhanced_simple",
        "version": "1.1",
        "features": [
            "Query classification",
            "Dynamic temperature (simplified)",
            "Basic caching",
            "Greeting without menu",
            "Complete item listings",
            "Multi-language support"
        ],
        "changes": "Removed advanced parameters for better compatibility"
    }

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics for simple cache"""
    try:
        from services.mia_chat_service_enhanced_simple import _simple_cache
        
        return {
            "status": "enabled",
            "type": "in-memory",
            "entries": len(_simple_cache),
            "message": "Using simple in-memory cache"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/cache/clear")
async def clear_cache(restaurant_id: str = None):
    """Clear cache for a specific restaurant or all"""
    try:
        from services.mia_chat_service_enhanced import cache
        
        if not cache.enabled:
            return {"status": "error", "message": "Cache is not enabled"}
        
        if restaurant_id:
            # Clear specific restaurant cache
            pattern = f"chat:*:{restaurant_id}:*"
            keys = cache.redis_client.keys(pattern)
            if keys:
                cache.redis_client.delete(*keys)
            return {"status": "success", "cleared": len(keys), "restaurant": restaurant_id}
        else:
            # Clear all cache
            cache.redis_client.flushdb()
            return {"status": "success", "message": "All cache cleared"}
            
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.get("/health")
async def health_check():
    """Health check for the enhanced chat service"""
    return {
        "status": "healthy",
        "provider": "mia_enhanced_simple",
        "version": "1.1",
        "enhanced_features": {
            "query_analysis": True,
            "dynamic_temperature": True,
            "conversation_memory": False,  # Disabled in simple version
            "caching": True,
            "simplified": True
        }
    }