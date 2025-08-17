"""
Test endpoint to verify Redis connectivity
"""
from fastapi import APIRouter
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/redis-check")
async def test_redis():
    """Test Redis connection and memory services"""
    results = {
        "redis_url": bool(os.getenv('REDIS_URL')),
        "redis_host": bool(os.getenv('REDIS_HOST')),
        "tests": {}
    }
    
    # Test 1: Direct Redis import
    try:
        import redis
        results["tests"]["redis_import"] = "✅ Redis package imported"
    except ImportError as e:
        results["tests"]["redis_import"] = f"❌ Redis import failed: {str(e)}"
    
    # Test 2: Redis connection
    try:
        import redis
        redis_url = os.getenv('REDIS_URL')
        if redis_url:
            r = redis.from_url(redis_url, decode_responses=True)
            r.ping()
            results["tests"]["redis_connection"] = "✅ Connected to Redis via URL"
        else:
            results["tests"]["redis_connection"] = "❌ No REDIS_URL found"
    except Exception as e:
        results["tests"]["redis_connection"] = f"❌ Connection failed: {str(e)}"
    
    # Test 3: Redis helper
    try:
        from services.redis_helper import redis_client
        redis_client.setex("test_key", 60, "test_value")
        value = redis_client.get("test_key")
        
        results["tests"]["redis_helper"] = {
            "status": "✅ Redis helper working",
            "using_real_redis": redis_client._redis_available,
            "test_passed": value == "test_value"
        }
    except Exception as e:
        results["tests"]["redis_helper"] = f"❌ Redis helper failed: {str(e)}"
    
    # Test 4: Memory services
    try:
        from services.conversation_memory_enhanced_lazy import enhanced_conversation_memory
        enhanced_conversation_memory.add_turn(
            "test-restaurant", 
            "test-client", 
            "Hello", 
            "Hi there!"
        )
        history = enhanced_conversation_memory.get_history("test-restaurant", "test-client")
        results["tests"]["memory_service"] = f"✅ Memory service working, stored {len(history)} turns"
    except Exception as e:
        results["tests"]["memory_service"] = f"❌ Memory service failed: {str(e)}"
    
    # Test 5: Available chat services
    try:
        from routes.chat_dynamic import chat_services
        results["available_chat_services"] = list(chat_services.keys())
    except Exception as e:
        results["available_chat_services"] = f"Error: {str(e)}"
    
    return results