"""
Enhanced MIA Direct API with Tool Calling Support
"""
import os
import json
import time
import logging
import requests
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

class MiaDirectAPI:
    """Direct API client for MIA backend with tool calling support"""
    
    def __init__(self):
        self.backend_url = os.getenv('MIA_BACKEND_URL', 'https://mia-backend-production.up.railway.app')
        self.timeout = 30
        
    def send_message_with_tools(self, prompt: str, system_prompt: str = None, 
                               tools: List[Dict] = None, context: Dict = None,
                               max_tokens: int = 150, temperature: float = 0.7) -> Dict:
        """Send message to MIA with optional tool definitions"""
        
        try:
            # Build request
            request_data = {
                "prompt": prompt,
                "system_prompt": system_prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "tools": tools,
                "context": context or {}
            }
            
            logger.info(f"Sending to MIA with {len(tools or [])} tools defined")
            
            # Submit job
            response = requests.post(
                f"{self.backend_url}/submit_job",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Failed to submit job: {response.status_code}")
                return {"response": "I'm having trouble connecting to the service."}
            
            job_data = response.json()
            job_id = job_data.get("job_id")
            
            if not job_id:
                logger.error("No job_id received")
                return {"response": "Service error occurred."}
            
            # Poll for result with fast polling
            result = self._fast_poll_result(job_id)
            
            # Extract response and check for tool calls
            if result:
                mia_response = result.get("result", {})
                
                # Check different response formats
                response_text = (
                    mia_response.get("response") or 
                    mia_response.get("text") or 
                    mia_response.get("output", "")
                )
                
                # Check for tool call
                tool_call = None
                if "tool_call" in mia_response:
                    tool_call = mia_response["tool_call"]
                elif "requires_tool_execution" in mia_response:
                    # Extract tool call from response
                    tool_call = self._extract_tool_call(response_text)
                
                return {
                    "response": response_text,
                    "tool_call": tool_call,
                    "job_id": job_id,
                    "tokens": mia_response.get("tokens_generated", 0)
                }
            
            return {"response": "I couldn't get a response in time."}
            
        except Exception as e:
            logger.error(f"Error sending message with tools: {e}")
            return {"response": "An error occurred while processing your request."}
    
    def send_tool_result(self, original_prompt: str, tool_call: Dict, 
                        tool_result: Dict, context: Dict = None,
                        max_tokens: int = 150) -> Dict:
        """Send tool execution result back to MIA for final response"""
        
        try:
            request_data = {
                "original_prompt": original_prompt,
                "tool_call": tool_call,
                "tool_result": tool_result,
                "context": context or {},
                "max_tokens": max_tokens,
                "temperature": 0.7
            }
            
            logger.info(f"Sending tool result for {tool_call.get('name')}")
            
            # Submit continuation job
            response = requests.post(
                f"{self.backend_url}/submit_job",
                json=request_data,
                headers={"Content-Type": "application/json"},
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                return {"response": "I couldn't process the information."}
            
            job_data = response.json()
            job_id = job_data.get("job_id")
            
            if not job_id:
                return {"response": "Service error occurred."}
            
            # Poll for final result
            result = self._fast_poll_result(job_id)
            
            if result:
                mia_response = result.get("result", {})
                response_text = (
                    mia_response.get("response") or 
                    mia_response.get("text") or 
                    mia_response.get("output", "")
                )
                
                return {
                    "response": response_text,
                    "tokens": mia_response.get("tokens_generated", 0)
                }
            
            return {"response": "I couldn't complete the request."}
            
        except Exception as e:
            logger.error(f"Error sending tool result: {e}")
            return {"response": "An error occurred while processing the information."}
    
    def _fast_poll_result(self, job_id: str, max_wait: int = 25) -> Optional[Dict]:
        """Fast polling strategy for MIA results"""
        
        poll_intervals = [
            (0.2, 25),  # First 5 seconds: every 200ms (25 checks)
            (0.5, 20),  # Next 10 seconds: every 500ms (20 checks)
            (1.0, 10)   # Remaining: every 1 second (10 checks)
        ]
        
        total_time = 0
        
        for interval, checks in poll_intervals:
            for _ in range(checks):
                if total_time >= max_wait:
                    return None
                
                try:
                    response = requests.get(
                        f"{self.backend_url}/get_result/{job_id}",
                        timeout=5
                    )
                    
                    if response.status_code == 200:
                        result = response.json()
                        if result.get("status") == "completed":
                            return result
                    
                except Exception as e:
                    logger.error(f"Polling error: {e}")
                
                time.sleep(interval)
                total_time += interval
        
        return None
    
    def _extract_tool_call(self, response_text: str) -> Optional[Dict]:
        """Extract tool call from response text"""
        
        # Look for tool call patterns
        import re
        
        # Pattern 1: <tool_call>{...}</tool_call>
        pattern1 = r'<tool_call>\s*({[^}]+})\s*</tool_call>'
        match = re.search(pattern1, response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Pattern 2: <function_call>{...}</function_call>
        pattern2 = r'<function_call>\s*({[^}]+})\s*</function_call>'
        match = re.search(pattern2, response_text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        
        # Pattern 3: JSON object with name and parameters
        pattern3 = r'{\s*"name"\s*:\s*"([^"]+)"\s*,\s*"parameters"\s*:\s*({[^}]+})\s*}'
        match = re.search(pattern3, response_text)
        if match:
            try:
                return {
                    "name": match.group(1),
                    "parameters": json.loads(match.group(2))
                }
            except json.JSONDecodeError:
                pass
        
        return None