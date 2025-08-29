"""
Debug endpoint to check memory state
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
import json
import redis
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

# Import memory stores from services
try:
    from services.rag_chat_memory_universal import MEMORY_STORE as universal_store
except:
    universal_store = {}

try:
    from services.rag_chat_memory_v6 import MEMORY_STORE as v6_store
except:
    v6_store = {}

# Redis client
try:
    redis_client = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
    redis_client.ping()
except:
    redis_client = None

@router.get("/check-memory/{restaurant_id}/{client_id}")
async def check_memory(restaurant_id: str, client_id: str, db: Session = Depends(get_db)):
    """Check memory state for a client"""
    
    result = {
        "restaurant_id": restaurant_id,
        "client_id": client_id,
        "memory_sources": {}
    }
    
    # Check universal memory store
    universal_key = f"universal_memory:{restaurant_id}:{client_id}"
    if universal_key in universal_store:
        result["memory_sources"]["universal_local"] = universal_store[universal_key]
    
    # Check v6 memory store
    v6_key = f"memory:{restaurant_id}:{client_id}"
    if v6_key in v6_store:
        result["memory_sources"]["v6_local"] = v6_store[v6_key]
    
    # Check Redis
    if redis_client:
        try:
            # Try universal key
            redis_data = redis_client.get(universal_key)
            if redis_data:
                result["memory_sources"]["universal_redis"] = json.loads(redis_data)
            
            # Try v6 key
            redis_data = redis_client.get(v6_key)
            if redis_data:
                result["memory_sources"]["v6_redis"] = json.loads(redis_data)
        except Exception as e:
            result["redis_error"] = str(e)
    
    # Check customer profiles table
    from models.customer_profile import CustomerProfile
    profile = db.query(CustomerProfile).filter(
        CustomerProfile.client_id == client_id,
        CustomerProfile.restaurant_id == restaurant_id
    ).first()
    
    if profile:
        result["customer_profile"] = {
            "name": profile.name,
            "allergies": profile.allergies,
            "dietary_restrictions": profile.dietary_restrictions,
            "preferences": profile.preferences
        }
    
    return result

@router.post("/clear-memory/{restaurant_id}/{client_id}")
async def clear_memory(restaurant_id: str, client_id: str):
    """Clear memory for testing"""
    
    # Clear universal store
    universal_key = f"universal_memory:{restaurant_id}:{client_id}"
    if universal_key in universal_store:
        del universal_store[universal_key]
    
    # Clear v6 store
    v6_key = f"memory:{restaurant_id}:{client_id}"
    if v6_key in v6_store:
        del v6_store[v6_key]
    
    # Clear Redis
    if redis_client:
        try:
            redis_client.delete(universal_key)
            redis_client.delete(v6_key)
        except:
            pass
    
    return {"status": "cleared"}