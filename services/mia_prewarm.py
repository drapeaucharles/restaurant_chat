"""
Pre-warm MIA backend to avoid cold start delays
"""
import requests
import logging
import os
import threading
import time

logger = logging.getLogger(__name__)

MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def prewarm_mia_backend():
    """Send a warm-up request to MIA backend"""
    try:
        logger.info("🔥 Pre-warming MIA backend...")
        
        # Simple warm-up prompt
        warmup_data = {
            "message": "Hello, this is a test. Please respond with 'OK'.",
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        # Send warm-up request
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=warmup_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-warmup"
            },
            timeout=5
        )
        
        if response.status_code == 200:
            result = response.json()
            job_id = result.get("job_id")
            
            if job_id:
                logger.info(f"✅ MIA pre-warm job submitted: {job_id}")
                
                # Poll once just to complete the request
                time.sleep(2)
                try:
                    poll_response = requests.get(
                        f"{MIA_BACKEND_URL}/job/{job_id}/result",
                        timeout=3
                    )
                    if poll_response.status_code == 200:
                        logger.info("✅ MIA backend is warmed up and ready!")
                except:
                    pass  # Don't worry if polling fails
            else:
                logger.info("✅ MIA backend responded directly - already warm!")
        else:
            logger.warning(f"MIA pre-warm got status {response.status_code}")
            
    except Exception as e:
        logger.warning(f"Could not pre-warm MIA: {e}")

def start_prewarm_thread():
    """Start pre-warming in a background thread"""
    thread = threading.Thread(target=prewarm_mia_backend, daemon=True)
    thread.start()
    logger.info("🚀 Started MIA pre-warm thread")

def periodic_keepalive(interval_minutes=10):
    """Keep MIA warm by sending periodic requests"""
    def keepalive_loop():
        while True:
            time.sleep(interval_minutes * 60)
            logger.info("🔄 Sending MIA keepalive...")
            prewarm_mia_backend()
    
    thread = threading.Thread(target=keepalive_loop, daemon=True)
    thread.start()
    logger.info(f"🔄 Started MIA keepalive (every {interval_minutes} minutes)")