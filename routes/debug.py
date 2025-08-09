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

@router.get("/debug/chat-provider")
def get_chat_provider():
    """Get current chat provider information"""
    from config import get_chat_provider_info
    return get_chat_provider_info()

@router.get("/debug/code-version")
def get_code_version():
    """Check which version of code is running"""
    import os
    import subprocess
    
    # Check if mia_chat_service has our fixes
    mia_path = os.path.join(os.path.dirname(__file__), "..", "services", "mia_chat_service.py")
    has_v3_fixes = False
    system_prompt_preview = "Unknown"
    
    try:
        with open(mia_path, 'r') as f:
            content = f.read()
            has_v3_fixes = "v3-291e0cc" in content or "ABSOLUTE REQUIREMENT" in content
            
            # Extract system prompt preview
            if "system_prompt = " in content:
                start = content.find('system_prompt = """') + 19
                end = content.find('"""', start)
                system_prompt_preview = content[start:start+100] + "..."
    except:
        pass
    
    # Git info
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()[:8]
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    except:
        commit = "unknown"
        branch = "unknown"
    
    return {
        "branch": branch,
        "commit": commit,
        "has_v3_fixes": has_v3_fixes,
        "system_prompt_preview": system_prompt_preview,
        "mia_chat_service_exists": os.path.exists(mia_path),
        "deployment_check": "v3-291e0cc"
    }

@router.get("/debug/test-pasta-context/{restaurant_id}")
def test_pasta_context(restaurant_id: str):
    """Test pasta context building directly"""
    from sqlalchemy.orm import Session
    from database import get_db
    import models
    from services.mia_chat_service import format_menu_for_context
    
    db = next(get_db())
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        return {"error": "Restaurant not found"}
    
    data = restaurant.data or {}
    menu_items = data.get("menu", [])
    
    # Build context for pasta query
    pasta_context = format_menu_for_context(menu_items, "what pasta do you have")
    
    # Also manually check pasta items
    pasta_found = []
    for i, item in enumerate(menu_items):
        name = item.get('name') or item.get('dish', '')
        if any(p in name.lower() for p in ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']):
            pasta_found.append(f"{i}: {name}")
    
    return {
        "total_menu_items": len(menu_items),
        "pasta_context": pasta_context,
        "pasta_items_found": len(pasta_found),
        "pasta_items": pasta_found[:10],
        "first_10_items": [f"{i}: {item.get('name') or item.get('dish', 'NO NAME')}" for i, item in enumerate(menu_items[:10])]
    }