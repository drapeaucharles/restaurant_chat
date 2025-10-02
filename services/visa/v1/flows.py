# services/visa/v1/flows.py
"""
Visa Agency Flow Registry and Orchestration
Multi-flow AI orchestration for visa processing
"""

import os
import requests
import json
import logging
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from .tools import get_visa_tools, execute_visa_tool

logger = logging.getLogger(__name__)
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")


class VisaFlowOrchestrator:
    """
    Multi-flow AI orchestration for visa agency
    Implements router → profiler → normalizer → recommender → clarifier → explainer/quote → application/checklist → tracker
    """
    
    def __init__(self, db: Session, business_id: str):
        self.db = db
        self.business_id = business_id
        self.tools = get_visa_tools(db)
    
    def process_message(self, message: str, client_id: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process incoming message through visa flow orchestration
        
        Args:
            message: User message
            client_id: Client identifier
            chat_history: Previous conversation history
        
        Returns:
            {
                "answer": str,
                "flow_used": str,
                "tools_executed": list,
                "next_suggested_actions": list
            }
        """
        try:
            chat_history = chat_history or []
            
            # Step 1: Router - Classify intent and extract profile data
            router_result = self._execute_flow("visa.v1.router", {
                "message": message,
                "chat_history": chat_history
            })
            
            intent = router_result.get("intent", "provide_profile_data")
            profile_delta = router_result.get("profile_delta", {})
            
            # Step 2: Update profile if we have new data
            if profile_delta:
                self.tools.profile_upsert_partial(client_id, self.business_id, profile_delta)
            
            # Step 3: Route to appropriate flow based on intent
            if intent == "provide_profile_data":
                return self._handle_profile_flow(message, client_id, chat_history)
            elif intent == "ask_recommendation":
                return self._handle_recommendation_flow(message, client_id, chat_history)
            elif intent == "ask_status":
                return self._handle_status_flow(message, client_id, chat_history)
            elif intent == "upload_document":
                return self._handle_upload_flow(message, client_id, chat_history)
            elif intent == "ask_price":
                return self._handle_pricing_flow(message, client_id, chat_history)
            elif intent == "ask_requirements":
                return self._handle_requirements_flow(message, client_id, chat_history)
            elif intent == "ask_processing_time":
                return self._handle_processing_time_flow(message, client_id, chat_history)
            elif intent == "handoff_human":
                return self._handle_handoff_flow(message, client_id, chat_history)
            else:
                # Default to profile flow
                return self._handle_profile_flow(message, client_id, chat_history)
                
        except Exception as e:
            logger.error(f"Error in visa flow orchestration: {str(e)}")
            return {
                "answer": "I apologize, but I'm having trouble processing your request right now. Please try again or contact our support team.",
                "flow_used": "error",
                "tools_executed": [],
                "next_suggested_actions": ["Contact support", "Try again later"]
            }
    
    def _handle_profile_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle profile data collection and completion"""
        try:
            # Get current profile
            profile_result = self.tools.profile_upsert_partial(client_id, self.business_id, {})
            profile = profile_result.get("profile", {})
            completeness = profile_result.get("completeness", 0.0)
            
            # Get missing fields
            missing_fields = self.tools.profile_get_missing_fields(profile)
            
            if completeness >= 0.8:
                # Profile is complete enough, move to recommendation
                return self._handle_recommendation_flow(message, client_id, chat_history)
            
            # Use profiler flow to ask for missing information
            profiler_result = self._execute_flow("visa.v1.profiler", {
                "profile_snapshot": profile,
                "last_questions": self._get_last_questions(chat_history),
                "user_reply": message
            })
            
            return {
                "answer": profiler_result.get("human_reply", "Could you provide more information about your travel plans?"),
                "flow_used": "profiler",
                "tools_executed": ["profile.upsert_partial"],
                "next_suggested_actions": ["Provide missing information"]
            }
            
        except Exception as e:
            logger.error(f"Error in profile flow: {str(e)}")
            raise
    
    def _handle_recommendation_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle visa recommendation based on profile"""
        try:
            # Get profile and normalize
            profile_result = self.tools.profile_upsert_partial(client_id, self.business_id, {})
            profile = profile_result.get("profile", {})
            
            # Normalize profile to case
            policy_result = self.tools.policypack_resolve(self.business_id)
            policy_data = policy_result.get("data", {})
            
            from .policy_tools import normalize_profile_to_case
            normalized_result = normalize_profile_to_case(profile, policy_data)
            normalized_case = normalized_result.get("normalized_case", {})
            
            # Evaluate eligibility
            evaluation_result = self.tools.rules_evaluate(self.business_id, normalized_case)
            options = evaluation_result.get("options", [])
            
            # Use recommender flow to generate response
            recommender_result = self._execute_flow("visa.v1.recommender", {
                "message": message,
                "profile": profile,
                "options": options
            })
            
            return {
                "answer": recommender_result.get("response", "Based on your profile, here are your visa options..."),
                "flow_used": "recommender",
                "tools_executed": ["rules.evaluate", "policypack.resolve"],
                "next_suggested_actions": ["Choose visa type", "Ask for details", "Get quote"]
            }
            
        except Exception as e:
            logger.error(f"Error in recommendation flow: {str(e)}")
            raise
    
    def _handle_status_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle application status inquiries"""
        try:
            # This would need application ID extraction from message or client context
            # For now, return a placeholder response
            
            tracker_result = self._execute_flow("visa.v1.tracker", {
                "message": message,
                "client_id": client_id
            })
            
            return {
                "answer": tracker_result.get("response", "I'd be happy to check your application status. Could you provide your application ID?"),
                "flow_used": "tracker",
                "tools_executed": [],
                "next_suggested_actions": ["Provide application ID", "Contact support"]
            }
            
        except Exception as e:
            logger.error(f"Error in status flow: {str(e)}")
            raise
    
    def _handle_upload_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle document upload requests"""
        try:
            application_result = self._execute_flow("visa.v1.application", {
                "message": message,
                "client_id": client_id,
                "action": "upload"
            })
            
            return {
                "answer": application_result.get("response", "I can help you with document uploads. Which document would you like to upload?"),
                "flow_used": "application",
                "tools_executed": [],
                "next_suggested_actions": ["Upload document", "Check requirements"]
            }
            
        except Exception as e:
            logger.error(f"Error in upload flow: {str(e)}")
            raise
    
    def _handle_pricing_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle pricing and quote requests"""
        try:
            # Get profile to determine applicable visa types
            profile_result = self.tools.profile_upsert_partial(client_id, self.business_id, {})
            profile = profile_result.get("profile", {})
            
            explainer_result = self._execute_flow("visa.v1.explainer", {
                "message": message,
                "profile": profile,
                "focus": "pricing"
            })
            
            return {
                "answer": explainer_result.get("response", "I can provide pricing information. Which visa type are you interested in?"),
                "flow_used": "explainer",
                "tools_executed": ["profile.upsert_partial"],
                "next_suggested_actions": ["Get quote", "Compare options", "Start application"]
            }
            
        except Exception as e:
            logger.error(f"Error in pricing flow: {str(e)}")
            raise
    
    def _handle_requirements_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle requirements inquiries"""
        try:
            explainer_result = self._execute_flow("visa.v1.explainer", {
                "message": message,
                "focus": "requirements"
            })
            
            return {
                "answer": explainer_result.get("response", "I can explain the requirements for different visa types. Which visa are you interested in?"),
                "flow_used": "explainer", 
                "tools_executed": [],
                "next_suggested_actions": ["Choose visa type", "Get checklist", "Start application"]
            }
            
        except Exception as e:
            logger.error(f"Error in requirements flow: {str(e)}")
            raise
    
    def _handle_processing_time_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle processing time inquiries"""
        try:
            explainer_result = self._execute_flow("visa.v1.explainer", {
                "message": message,
                "focus": "timing"
            })
            
            return {
                "answer": explainer_result.get("response", "Processing times vary by visa type. Which visa are you interested in?"),
                "flow_used": "explainer",
                "tools_executed": [],
                "next_suggested_actions": ["Choose visa type", "Get timeline", "Consider express processing"]
            }
            
        except Exception as e:
            logger.error(f"Error in processing time flow: {str(e)}")
            raise
    
    def _handle_handoff_flow(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """Handle requests to speak with human agent"""
        try:
            return {
                "answer": "I'll connect you with one of our visa specialists. Please hold on while I transfer you to a human agent who can provide personalized assistance with your visa application.",
                "flow_used": "handoff",
                "tools_executed": [],
                "next_suggested_actions": ["Wait for agent", "Provide contact details"]
            }
            
        except Exception as e:
            logger.error(f"Error in handoff flow: {str(e)}")
            raise
    
    def _execute_flow(self, flow_name: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific flow using MIA backend"""
        try:
            prompt = self._get_flow_prompt(flow_name, context)
            
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={
                    "message": prompt,
                    "max_tokens": 300,
                    "temperature": 0.3
                },
                timeout=30
            )
            
            if response.status_code != 200:
                raise Exception(f"MIA backend error: {response.status_code}")
            
            result = response.json()
            response_text = result.get("response", "")
            
            # Try to parse JSON response
            try:
                return json.loads(response_text)
            except json.JSONDecodeError:
                # If not JSON, return as text response
                return {"response": response_text}
                
        except Exception as e:
            logger.error(f"Error executing flow {flow_name}: {str(e)}")
            raise
    
    def _get_flow_prompt(self, flow_name: str, context: Dict[str, Any]) -> str:
        """Get prompt for specific flow"""
        prompts = {
            "visa.v1.router": self._get_router_prompt(context),
            "visa.v1.profiler": self._get_profiler_prompt(context),
            "visa.v1.recommender": self._get_recommender_prompt(context),
            "visa.v1.explainer": self._get_explainer_prompt(context),
            "visa.v1.application": self._get_application_prompt(context),
            "visa.v1.tracker": self._get_tracker_prompt(context)
        }
        
        return prompts.get(flow_name, "Process this visa-related request.")
    
    def _get_router_prompt(self, context: Dict[str, Any]) -> str:
        """Router flow prompt"""
        message = context.get("message", "")
        
        return f"""Classify the user message for visa agency chat.
Output strict JSON: {{"intent":"...", "profile_delta":{{...}}}}.

Intents: provide_profile_data, ask_recommendation, ask_status, upload_document, ask_price, ask_requirements, ask_processing_time, handoff_human.

Extract any profile facts in free text (nationality_iso2, purpose, intended_stay_days, earliest_travel_date, passport_validity_months, has_return_ticket, funds_usd, invitation_letter).

Do not answer users here.

User message: "{message}"
"""
    
    def _get_profiler_prompt(self, context: Dict[str, Any]) -> str:
        """Profiler flow prompt"""
        profile = context.get("profile_snapshot", {})
        last_questions = context.get("last_questions", [])
        user_reply = context.get("user_reply", "")
        
        return f"""Input: profile_snapshot: {json.dumps(profile)}, last_questions: {last_questions}, user_reply: "{user_reply}".

Normalize any fields in reply into "patch".
If only 1 of the last 2 was answered, ask only the other.
If 0 answered, ask the first two highest-priority missing fields.

Priority: purpose → nationality_iso2 → intended_stay_days → earliest_travel_date → passport_validity_months → has_return_ticket → funds_usd → invitation_letter

Output strict JSON:
{{ "patch":{{}}, "extracted_from_reply":[], "unanswered_from_last":[],
  "still_missing_overall":[], "next_questions":[], "human_reply":"..." }}
"""
    
    def _get_recommender_prompt(self, context: Dict[str, Any]) -> str:
        """Recommender flow prompt"""
        profile = context.get("profile", {})
        options = context.get("options", [])
        
        return f"""Use rules.evaluate() results to recommend top 2–3 visa options.

Profile: {json.dumps(profile)}
Options: {json.dumps(options)}

Return top options + one-line rationales + tiny comparison table showing:
- Visa code
- Stay duration  
- Extendable to
- Convertible
- Sponsor needed
- Government fee
- Processing time

If none eligible, state why and suggest the single fix needed.

Provide natural, helpful response focusing on best options for the customer.
"""
    
    def _get_explainer_prompt(self, context: Dict[str, Any]) -> str:
        """Explainer flow prompt"""
        focus = context.get("focus", "general")
        message = context.get("message", "")
        
        if focus == "pricing":
            return f"""Explain visa pricing and fees for Indonesian visas.

User question: "{message}"

Provide clear breakdown of:
- Government fees
- Service fees  
- Optional add-ons
- Payment options

Include call-to-action: [Get Quote] [Compare Options] [Start Application]
"""
        elif focus == "requirements":
            return f"""Explain visa requirements and documentation.

User question: "{message}"

Cover key requirements:
- Passport validity
- Photos
- Financial proof
- Supporting documents
- Processing steps

Include call-to-action: [Get Checklist] [Start Application] [Talk to Agent]
"""
        elif focus == "timing":
            return f"""Explain visa processing times and timelines.

User question: "{message}"

Cover:
- Standard processing times
- Express options
- Factors affecting timing
- Collection process

Include call-to-action: [Start Application] [Express Processing] [Check Status]
"""
        else:
            return f"""Provide helpful information about Indonesian visas.

User question: "{message}"

Be informative and guide toward next steps.
"""
    
    def _get_application_prompt(self, context: Dict[str, Any]) -> str:
        """Application flow prompt"""
        message = context.get("message", "")
        action = context.get("action", "general")
        
        return f"""Handle visa application management.

User message: "{message}"
Action: {action}

Confirm app creation; present 3–5 top checklist items; accept uploads; create paylinks on request; keep updates concise.

Focus on practical next steps and clear guidance.
"""
    
    def _get_tracker_prompt(self, context: Dict[str, Any]) -> str:
        """Tracker flow prompt"""
        message = context.get("message", "")
        
        return f"""Handle application status tracking.

User message: "{message}"

Translate status to human text; highlight deadlines (extension window, collection, payment expiry); propose one next action.

Be specific about timelines and next steps.
"""
    
    def _get_last_questions(self, chat_history: List[Dict]) -> List[str]:
        """Extract last questions asked by the assistant"""
        questions = []
        for msg in reversed(chat_history[-4:]):  # Look at last 4 messages
            if msg.get("role") == "assistant" and "?" in msg.get("message", ""):
                questions.append(msg["message"])
                if len(questions) >= 2:
                    break
        return questions[:2]
