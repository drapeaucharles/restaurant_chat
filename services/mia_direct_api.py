"""
Direct API call to MIA without polling (experimental)
"""
import requests
import logging
import os
import json

logger = logging.getLogger(__name__)

MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def get_mia_response_direct(prompt: str, params: dict) -> str:
    """Try to get a direct synchronous response from MIA"""
    try:
        request_data = {
            "message": prompt,
            "max_tokens": params.get("max_tokens", 200),
            "temperature": params.get("temperature", 0.7),
            "sync": True,  # Request synchronous processing if supported
            "wait_for_result": True  # Tell MIA to wait for completion
        }
        
        logger.info(f"Attempting direct MIA call (no polling)")
        
        # Try with a long timeout for synchronous response
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-direct",
                "X-Request-Mode": "synchronous"  # Hint to MIA
            },
            timeout=60  # 60 second timeout for direct response
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if we got a direct response (no job_id)
            if not result.get("job_id"):
                # Direct response formats
                text = (result.get("response") or 
                       result.get("text") or 
                       result.get("answer") or 
                       result.get("output", ""))
                
                if text:
                    logger.info(f"Got direct MIA response (no polling needed!)")
                    return text.strip()
            
            # If we still get a job_id, MIA doesn't support sync mode
            logger.info("MIA returned job_id - sync mode not supported")
            
        else:
            logger.error(f"MIA direct call failed: {response.status_code}")
            
    except requests.exceptions.Timeout:
        logger.info("Direct call timed out - MIA likely doesn't support sync mode")
    except Exception as e:
        logger.error(f"Error in direct MIA call: {e}")
    
    # Fall back to polling method
    logger.info("Falling back to polling method")
    from services.mia_chat_service_hybrid import get_mia_response_hybrid
    return get_mia_response_hybrid(prompt, params)

def test_mia_sync_support():
    """Test if MIA supports synchronous responses"""
    try:
        # Simple test request
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json={
                "message": "Hi",
                "max_tokens": 10,
                "sync": True
            },
            headers={"Content-Type": "application/json"},
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            if not result.get("job_id"):
                logger.info("✅ MIA supports synchronous mode!")
                return True
            else:
                logger.info("❌ MIA only supports async/polling mode")
                return False
    except:
        pass
    
    return False