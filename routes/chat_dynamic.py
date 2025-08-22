"""
Dynamic chat endpoint that uses restaurant-specific RAG mode
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

# Import all available services
chat_services = {}

# Load optimized service
try:
    from services.rag_chat_optimized import optimized_rag_service
    chat_services['optimized'] = optimized_rag_service
    logger.info("Loaded optimized RAG service")
except ImportError:
    logger.warning("Optimized RAG service not available")

# Load enhanced v2 service
try:
    from services.rag_chat_enhanced_v2 import enhanced_rag_service_v2
    chat_services['enhanced_v2'] = enhanced_rag_service_v2
    logger.info("Loaded enhanced v2 RAG service")
except ImportError:
    logger.warning("Enhanced v2 RAG service not available")

# Load enhanced v3 service
try:
    from services.rag_chat_enhanced_v3 import enhanced_rag_chat_v3
    chat_services['enhanced_v3'] = enhanced_rag_chat_v3
    logger.info("Loaded enhanced v3 RAG service")
except ImportError:
    logger.warning("Enhanced v3 RAG service not available")

# Load hybrid smart service
try:
    from services.rag_chat_hybrid_smart import smart_hybrid_rag
    chat_services['hybrid_smart'] = smart_hybrid_rag
    logger.info("Loaded hybrid smart RAG service")
except ImportError:
    logger.warning("Hybrid smart RAG service not available")

# Load hybrid smart with memory service
try:
    from services.rag_chat_hybrid_smart_memory import smart_hybrid_memory_rag
    chat_services['hybrid_smart_memory'] = smart_hybrid_memory_rag
    logger.info("Loaded hybrid smart with memory RAG service")
except ImportError:
    logger.warning("Hybrid smart with memory RAG service not available")

# Load hybrid smart with memory V2 service (improved personal handling)
try:
    from services.rag_chat_hybrid_smart_memory_v2 import smart_hybrid_memory_rag_v2
    chat_services['hybrid_smart_memory_v2'] = smart_hybrid_memory_rag_v2
    logger.info("Loaded hybrid smart with memory V2 RAG service")
except ImportError:
    logger.warning("Hybrid smart with memory V2 RAG service not available")

# Load simple memory service (minimal dependencies)
try:
    from services.rag_chat_simple_memory import simple_memory_rag
    chat_services['simple_memory'] = simple_memory_rag
    logger.info("Loaded simple memory RAG service")
except ImportError:
    logger.warning("Simple memory RAG service not available")

# Load ultra simple service (absolutely minimal)
try:
    from services.rag_chat_ultra_simple import ultra_simple_rag
    chat_services['ultra_simple'] = ultra_simple_rag
    logger.info("Loaded ultra simple RAG service")
except ImportError:
    logger.warning("Ultra simple RAG service not available")

# Load optimized with memory service
try:
    from services.rag_chat_optimized_with_memory import optimized_rag_with_memory
    chat_services['optimized_with_memory'] = optimized_rag_with_memory
    logger.info("Loaded optimized with memory RAG service")
except ImportError:
    logger.warning("Optimized with memory RAG service not available")

# Load enhanced v3 with lazy Redis service
try:
    from services.rag_chat_enhanced_v3_lazy import enhanced_rag_chat_v3 as enhanced_v3_lazy
    chat_services['enhanced_v3_lazy'] = enhanced_v3_lazy
    logger.info("Loaded enhanced v3 lazy RAG service")
except ImportError:
    logger.warning("Enhanced v3 lazy RAG service not available")

# Load debug version
try:
    from services.rag_chat_enhanced_v3_debug import enhanced_rag_chat_v3_debug
    chat_services['enhanced_v3_debug'] = enhanced_rag_chat_v3_debug
    logger.info("Loaded enhanced v3 debug RAG service")
except ImportError:
    logger.warning("Enhanced v3 debug RAG service not available")

# Load working memory version
try:
    from services.rag_chat_memory_working import working_memory_rag
    chat_services['memory_working'] = working_memory_rag
    logger.info("Loaded working memory RAG service")
except ImportError:
    logger.warning("Working memory RAG service not available")

# Load best memory version (working + all features)
try:
    from services.rag_chat_memory_best import best_memory_rag
    chat_services['memory_best'] = best_memory_rag
    logger.info("Loaded best memory RAG service")
except ImportError:
    logger.warning("Best memory RAG service not available")

# Load fixed memory version
try:
    from services.rag_chat_memory_fixed import fixed_memory_rag
    chat_services['memory_fixed'] = fixed_memory_rag
    logger.info("Loaded fixed memory RAG service")
except ImportError:
    logger.warning("Fixed memory RAG service not available")

# Load diagnostic memory version
try:
    from services.rag_chat_memory_diagnostic import diagnostic_memory_rag
    chat_services['memory_diagnostic'] = diagnostic_memory_rag
    logger.info("Loaded diagnostic memory RAG service")
except ImportError:
    logger.warning("Diagnostic memory RAG service not available")

# Load memory v2 (working + query classification)
try:
    from services.rag_chat_memory_v2 import working_memory_rag_v2
    chat_services['memory_v2'] = working_memory_rag_v2
    logger.info("Loaded memory v2 RAG service")
except ImportError:
    logger.warning("Memory v2 RAG service not available")

# Load memory v3 (v2 + response validation)
try:
    from services.rag_chat_memory_v3 import working_memory_rag_v3
    chat_services['memory_v3'] = working_memory_rag_v3
    logger.info("Loaded memory v3 RAG service")
except ImportError:
    logger.warning("Memory v3 RAG service not available")

# Load memory v4 (v3 + allergen service)
try:
    from services.rag_chat_memory_v4 import working_memory_rag_v4
    chat_services['memory_v4'] = working_memory_rag_v4
    logger.info("Loaded memory v4 RAG service")
except ImportError:
    logger.warning("Memory v4 RAG service not available")

# Load memory v5 (v4 + context formatter)
try:
    from services.rag_chat_memory_v5 import working_memory_rag_v5
    chat_services['memory_v5'] = working_memory_rag_v5
    logger.info("Loaded memory v5 RAG service")
except ImportError:
    logger.warning("Memory v5 RAG service not available")

# Load memory v6 (v5 + extract_and_update_memory)
try:
    from services.rag_chat_memory_v6 import working_memory_rag_v6
    chat_services['memory_v6'] = working_memory_rag_v6
    logger.info("Loaded memory v6 RAG service")
except ImportError:
    logger.warning("Memory v6 RAG service not available")

# Load universal memory service (works for any business type)
try:
    from services.rag_chat_memory_universal import universal_memory_rag
    chat_services['memory_universal'] = universal_memory_rag
    logger.info("Loaded universal memory RAG service")
except ImportError:
    logger.warning("Universal memory RAG service not available")

# Fallback service
if not chat_services:
    logger.error("No RAG services available, using MIA hybrid as fallback")
    chat_services['fallback'] = mia_chat_service_hybrid

@router.post("/chat", response_model=ChatResponse)
async def dynamic_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """
    Dynamic chat endpoint that uses restaurant-specific RAG mode
    """
    try:
        logger.info(f"Dynamic chat request from client {req.client_id} to restaurant {req.restaurant_id}")
        
        # Get restaurant/business to check its RAG mode
        # First try businesses table (new universal model)
        from sqlalchemy import text
        business_query = text("""
            SELECT business_type, rag_mode 
            FROM businesses 
            WHERE business_id = :business_id
        """)
        business_result = db.execute(business_query, {"business_id": req.restaurant_id}).fetchone()
        
        if business_result:
            business_type, rag_mode = business_result
            # For non-restaurant businesses, use universal memory service
            if business_type != 'restaurant' and 'memory_universal' in chat_services:
                rag_mode = 'memory_universal'
                logger.info(f"Business {req.restaurant_id} is type '{business_type}', using universal memory service")
        else:
            # Fallback to restaurant model for backward compatibility
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                raise HTTPException(status_code=404, detail="Restaurant/Business not found")
            
            rag_mode = getattr(restaurant, 'rag_mode', 'hybrid_smart')
        
        # If restaurant doesn't have rag_mode set, use default from env or hybrid_smart
        if not rag_mode:
            rag_mode = os.getenv("DEFAULT_RAG_MODE", "hybrid_smart")
        
        logger.info(f"Restaurant {req.restaurant_id} using RAG mode: {rag_mode}")
        
        # Select appropriate service
        if rag_mode in chat_services:
            chat_service = chat_services[rag_mode]
            logger.info(f"Selected service: {rag_mode}")
        else:
            logger.warning(f"RAG mode '{rag_mode}' not available, falling back to hybrid_smart")
            chat_service = chat_services.get('hybrid_smart', chat_services.get('optimized', chat_services.get('fallback')))
        
        # Get or create client FIRST (before creating message)
        get_or_create_client(db, req.client_id, req.restaurant_id)
        
        # Now create client message
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type=req.sender_type,
            message=req.message
        )
        db.add(new_message)
        db.commit()
        
        # Get AI response using selected service with fallback
        try:
            response = chat_service(req, db)
            
            # Log which service was used
            response_dict = response.dict() if hasattr(response, 'dict') else response
            if isinstance(response_dict, dict) and 'answer' in response_dict:
                logger.info(f"Response generated using {rag_mode} mode")
            
            return response
        except Exception as service_error:
            logger.error(f"Service {rag_mode} failed: {service_error}")
            logger.info("Falling back to MIA hybrid service")
            
            # Fallback to MIA hybrid service
            try:
                fallback_response = mia_chat_service_hybrid(req, db)
                logger.info("Fallback service succeeded")
                return fallback_response
            except Exception as fallback_error:
                logger.error(f"Fallback service also failed: {fallback_error}")
                # Return a basic error response
                from schemas.chat import ChatResponse
                return ChatResponse(answer="I apologize, but I'm experiencing technical difficulties. Please try again later.")
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in dynamic chat endpoint: {e}")
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/provider")
async def get_provider_info():
    """Get information about available chat providers"""
    return {
        "provider": "dynamic_rag",
        "available_modes": list(chat_services.keys()),
        "default_mode": os.getenv("DEFAULT_RAG_MODE", "hybrid_smart"),
        "features": [
            "Restaurant-specific AI mode selection",
            "Dynamic service routing",
            "Fallback support",
            "All RAG modes available"
        ]
    }