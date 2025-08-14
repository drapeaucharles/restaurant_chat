"""
Enhanced chat endpoint with improved AI service
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
import models
from schemas.chat import ChatRequest, ChatResponse
from datetime import datetime
from services.mia_chat_service_hybrid import mia_chat_service_hybrid, get_or_create_client
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter()

# Use the hybrid service (Maria personality + MIA compatibility)
chat_service = mia_chat_service_hybrid

@router.post("/chat", response_model=ChatResponse)
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
        "provider": "mia_hybrid",
        "version": "2.0",
        "features": [
            "Maria personality assistant",
            "Redis caching with fallback",
            "Query classification",
            "Dynamic temperature adjustment",
            "Multi-language support (EN/ES/FR)",
            "Complete menu listings",
            "MIA-compatible parameters"
        ],
        "changes": "Combines Maria personality with MIA compatibility"
    }

@router.get("/cache/stats")
async def get_cache_stats():
    """Get cache statistics for hybrid cache"""
    try:
        from services.mia_chat_service_hybrid import cache
        
        stats = cache.get_stats()
        return {
            "status": "enabled",
            "type": "hybrid" if stats["redis_available"] else "in-memory",
            "redis_available": stats["redis_available"],
            "in_memory_entries": stats["in_memory_entries"],
            "in_memory_size": stats["in_memory_size"],
            "message": "Using hybrid cache with Redis + in-memory fallback"
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/cache/clear")
async def clear_cache(restaurant_id: str = None):
    """Clear cache for a specific restaurant or all"""
    try:
        from services.mia_chat_service_hybrid import cache
        
        if restaurant_id:
            # Clear specific restaurant cache
            cleared = cache.clear_pattern(f"*:{restaurant_id}:*")
            return {"status": "success", "cleared": cleared, "restaurant": restaurant_id}
        else:
            # Clear all cache
            cache.clear_all()
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

@router.post("/debug")
async def debug_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Debug endpoint to see what's being sent to MIA"""
    from services.mia_chat_service_hybrid import (
        HybridQueryClassifier, 
        get_maria_system_prompt,
        get_hybrid_parameters,
        build_hybrid_context,
        detect_language
    )
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        return {"error": "Restaurant not found"}
    
    # Detect language
    language = detect_language(req.message)
    
    # Classify query
    query_type = HybridQueryClassifier.classify(req.message)
    
    # Get restaurant data
    data = restaurant.data or {}
    restaurant_name = data.get('restaurant_name', req.restaurant_id)
    menu_items = data.get("menu", [])
    
    # Build prompt
    system_prompt = get_maria_system_prompt(restaurant_name, query_type, language)
    context = build_hybrid_context(menu_items, query_type, req.message)
    
    full_prompt = system_prompt
    if context:
        full_prompt += "\n" + context
    persona_name = "Maria" if language == "en" else ("María" if language == "es" else "Marie")
    full_prompt += f"\n\nCustomer: {req.message}\n{persona_name}:"
    
    # Get parameters
    params = get_hybrid_parameters(query_type)
    
    return {
        "language": language,
        "maria_persona": persona_name,
        "query_type": query_type.value,
        "parameters": params,
        "prompt_length": len(full_prompt),
        "prompt_preview": full_prompt[:500] + "..." if len(full_prompt) > 500 else full_prompt,
        "menu_items_count": len(menu_items),
        "restaurant_name": restaurant_name,
        "context_preview": context[:200] + "..." if len(context) > 200 else context
    }

@router.get("/test-mia")
async def test_mia_direct():
    """Test MIA backend directly"""
    import requests
    
    test_prompt = "Hello! I am a test. Please respond with a greeting."
    
    try:
        response = requests.post(
            f"{os.getenv('MIA_BACKEND_URL', 'https://mia-backend-production.up.railway.app')}/api/generate",
            json={
                "prompt": test_prompt,
                "max_tokens": 50,
                "temperature": 0.7,
                "source": "test-endpoint"
            },
            timeout=10
        )
        
        return {
            "status_code": response.status_code,
            "headers": dict(response.headers),
            "response": response.json() if response.status_code == 200 else response.text,
            "test_prompt": test_prompt
        }
    except Exception as e:
        return {
            "error": str(e),
            "type": type(e).__name__
        }

@router.post("/test-service")
async def test_service_flow(req: ChatRequest, db: Session = Depends(get_db)):
    """Test the entire service flow with detailed output"""
    from services.mia_chat_service_hybrid import (
        HybridQueryClassifier,
        get_maria_system_prompt,
        get_hybrid_parameters,
        build_hybrid_context,
        get_mia_response_hybrid,
        detect_language
    )
    
    steps = []
    
    # Step 1: Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        return {"error": "Restaurant not found", "steps": steps}
    
    steps.append({"step": "restaurant_found", "success": True})
    
    # Step 2: Detect language
    language = detect_language(req.message)
    steps.append({"step": "language_detected", "language": language})
    
    # Step 3: Classify query
    query_type = HybridQueryClassifier.classify(req.message)
    steps.append({"step": "query_classified", "type": query_type.value})
    
    # Step 4: Get data
    data = restaurant.data or {}
    restaurant_name = data.get('restaurant_name', req.restaurant_id)
    menu_items = data.get("menu", [])
    steps.append({"step": "data_loaded", "menu_count": len(menu_items)})
    
    # Step 5: Build prompt
    system_prompt = get_maria_system_prompt(restaurant_name, query_type, language)
    context = build_hybrid_context(menu_items, query_type, req.message)
    full_prompt = system_prompt
    if context:
        full_prompt += "\n" + context
    persona_name = "Maria" if language == "en" else ("María" if language == "es" else "Marie")
    full_prompt += f"\n\nCustomer: {req.message}\n{persona_name}:"
    steps.append({"step": "prompt_built", "length": len(full_prompt), "maria_persona": persona_name})
    
    # Step 6: Get parameters
    params = get_hybrid_parameters(query_type)
    steps.append({"step": "params_set", "params": params})
    
    # Step 7: Call MIA
    try:
        answer = get_mia_response_hybrid(full_prompt, params)
        steps.append({"step": "mia_called", "response_length": len(answer), "response_preview": answer[:100]})
    except Exception as e:
        steps.append({"step": "mia_error", "error": str(e)})
        answer = f"Error calling MIA: {e}"
    
    return {
        "steps": steps,
        "final_answer": answer,
        "prompt_preview": full_prompt[:300] + "..."
    }