"""
Optimized MIA polling service with faster response times
"""
import requests
import time
import logging
import os
import json

logger = logging.getLogger(__name__)

MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")

def get_mia_response_fast(prompt: str, params: dict) -> str:
    """Get response from MIA with optimized polling"""
    try:
        request_data = {
            "message": prompt,
            "max_tokens": params.get("max_tokens", 200),
            "temperature": params.get("temperature", 0.7)
        }
        
        logger.info(f"Sending to MIA (fast polling): {len(prompt)} chars")
        
        # Initial request
        response = requests.post(
            f"{MIA_BACKEND_URL}/chat",
            json=request_data,
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-fast"
            },
            timeout=10  # Shorter timeout for initial request
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # Check if it's a job response
            job_id = result.get("job_id")
            if job_id:
                logger.info(f"Job queued with ID: {job_id}, fast polling...")
                
                # Optimized polling strategy
                # First 5 seconds: poll every 0.2 seconds (25 checks)
                # Next 10 seconds: poll every 0.5 seconds (20 checks)
                # Remaining: poll every 1 second
                
                start_time = time.time()
                poll_count = 0
                
                while time.time() - start_time < 30:  # 30 second max
                    poll_count += 1
                    elapsed = time.time() - start_time
                    
                    # Determine polling interval
                    if elapsed < 5:
                        time.sleep(0.2)  # Fast polling initially
                    elif elapsed < 15:
                        time.sleep(0.5)  # Medium polling
                    else:
                        time.sleep(1.0)  # Slower polling
                    
                    try:
                        poll_response = requests.get(
                            f"{MIA_BACKEND_URL}/job/{job_id}/result",
                            timeout=3  # Short timeout for polling
                        )
                        
                        if poll_response.status_code == 200:
                            poll_result = poll_response.json()
                            
                            if poll_result.get("result"):
                                # Handle different response formats
                                result_data = poll_result["result"]
                                if isinstance(result_data, str):
                                    text = result_data
                                elif isinstance(result_data, dict):
                                    text = result_data.get("text") or result_data.get("response") or result_data.get("output", "")
                                else:
                                    text = str(result_data)
                                
                                if text:
                                    total_time = time.time() - start_time
                                    logger.info(f"Got MIA response in {total_time:.1f}s after {poll_count} polls")
                                    return text.strip()
                                    
                            elif poll_result.get("status") == "failed":
                                logger.error(f"Job {job_id} failed")
                                break
                                
                    except requests.exceptions.Timeout:
                        logger.debug(f"Poll timeout at {elapsed:.1f}s, continuing...")
                        continue
                    except Exception as e:
                        logger.debug(f"Poll error: {e}, continuing...")
                        continue
                
                logger.warning(f"Polling timed out after {poll_count} attempts")
                
            else:
                # Direct response (no job ID)
                return result.get("response", result.get("text", "I'm having trouble processing that."))
                
        else:
            logger.error(f"MIA error: {response.status_code} - {response.text}")
            
    except Exception as e:
        logger.error(f"MIA fast polling error: {e}")
    
    return "I apologize, but I'm having trouble connecting to my knowledge base. Please try again."

def get_mia_response_with_retry(prompt: str, params: dict, max_retries: int = 2) -> str:
    """Get MIA response with retry logic"""
    for attempt in range(max_retries):
        try:
            response = get_mia_response_fast(prompt, params)
            if response and not response.startswith("I apologize"):
                return response
        except Exception as e:
            logger.error(f"Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                time.sleep(0.5)  # Brief pause before retry
    
    # Fallback to original function if all retries fail
    from services.mia_chat_service_hybrid import get_mia_response_hybrid
    logger.info("Falling back to standard MIA polling")
    return get_mia_response_hybrid(prompt, params)