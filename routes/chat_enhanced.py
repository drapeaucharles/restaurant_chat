"""
Enhanced chat endpoint with improved AI service
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from datetime import datetime
from services.mia_chat_service_enhanced import mia_chat_service_enhanced, get_or_create_client
import logging
import config_enhanced

logger = logging.getLogger(__name__)

router = APIRouter()

# Get the configured chat service
chat_service = config_enhanced.get_chat_service()

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
    return config_enhanced.get_provider_info()

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics (if Redis is enabled)"""
    try:
        from services.mia_chat_service_enhanced import cache
        
        if not cache.enabled:
            return {"status": "disabled", "message": "Cache is not enabled"}
        
        # Get some basic stats
        info = cache.redis_client.info()
        return {
            "status": "enabled",
            "used_memory": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0),
            "keyspace": info.get("db0", {})
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
        "provider": config_enhanced.CHAT_PROVIDER,
        "enhanced_features": {
            "query_analysis": config_enhanced.ENABLE_QUERY_ANALYSIS,
            "dynamic_temperature": config_enhanced.ENABLE_DYNAMIC_TEMPERATURE,
            "conversation_memory": config_enhanced.ENABLE_CONVERSATION_MEMORY,
            "caching": config_enhanced.CACHE_ENABLED
        }
    }