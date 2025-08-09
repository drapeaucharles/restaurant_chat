"""
Version endpoint to track deployments
"""
from fastapi import APIRouter
import subprocess
import os

router = APIRouter(tags=["version"])

@router.get("/version")
def get_version():
    """Get current code version"""
    try:
        # Try to get git commit hash
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()[:8]
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
        
        # Check if specific files exist (to verify deployment)
        has_debug_pasta = os.path.exists('routes/debug_pasta.py')
        
        return {
            "version": "1.0.1",
            "commit": commit,
            "branch": branch,
            "has_debug_pasta_route": has_debug_pasta,
            "deployment_test": "v3-d6240fc"  # Latest commit marker
        }
    except:
        return {
            "version": "1.0.1",
            "error": "Could not get git info",
            "deployment_test": "v3-d6240fc"
        }