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