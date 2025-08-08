"""
Debug endpoints to help troubleshoot deployment issues
"""
from fastapi import APIRouter

router = APIRouter(tags=["debug"])

@router.get("/debug/health")
def debug_health():
    """Simple health check that should always work"""
    return {"status": "ok", "message": "Debug endpoint working"}

@router.get("/debug/imports")
def debug_imports():
    """Test if imports are working"""
    try:
        import models
        models_ok = True
    except Exception as e:
        models_ok = str(e)
    
    try:
        from services.mia_chat_service import mia_chat_service
        mia_service_ok = True
    except Exception as e:
        mia_service_ok = str(e)
    
    try:
        from config import get_chat_provider_info
        config_ok = True
    except Exception as e:
        config_ok = str(e)
    
    return {
        "models": models_ok,
        "mia_service": mia_service_ok,
        "config": config_ok
    }