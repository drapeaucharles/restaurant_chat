# services/visa_chat_service_hybrid.py
"""
Hybrid Visa Chat Service - Best of Both Worlds
- Uses WorkingVisaFlowOrchestrator for routing and profile management
- Uses AI for natural response generation
- Maintains conversation context and progression
"""

import json
import logging
import requests
import os
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse
from .visa_flow_orchestrator_working import WorkingVisaFlowOrchestrator

logger = logging.getLogger(__name__)
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")


class HybridVisaService:
    """
    Hybrid service combining orchestrator structure with AI responses
    """
    
    def __init__(self, db: Session, business_id: str):
        self.db = db
        self.business_id = business_id
        self.orchestrator = WorkingVisaFlowOrchestrator(db, business_id)
    
    def process_message(self, message: str, client_id: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process message using hybrid approach:
        1. Use orchestrator for routing and profile management
        2. Use AI for natural response generation
        3. Maintain conversation context and progression
        """
        try:
            client_id = str(client_id)
            chat_history = chat_history or []
            
            # Step 1: Use orchestrator for routing and profile extraction
            router_result = self.orchestrator._flow_router(message, chat_history)
            intent = router_result["intent"]
            profile_delta = router_result.get("profile_delta", {})
            
            # Step 2: Update profile if needed
            if profile_delta:
                logger.info(f"🔄 Updating profile for {client_id}: {profile_delta}")
                self.orchestrator._flow_profiler(client_id, profile_delta)
            
            # Step 3: Get current complete profile
            current_profile = self._get_current_profile(client_id)
            
            # Step 4: Generate AI response based on intent and context
            ai_response = self._generate_contextual_ai_response(
                message=message,
                intent=intent,
                profile=current_profile,
                profile_delta=profile_delta,
                chat_history=chat_history
            )
            
            return {
                "answer": ai_response,
                "flow_used": f"hybrid_{intent}",
                "tools_executed": ["profile_extraction", "ai_generation"],
                "next_suggested_actions": self._get_next_actions(intent, current_profile)
            }
            
        except Exception as e:
            logger.error(f"❌ Hybrid service error: {e}")
            return {
                "answer": "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa inquiry.",
                "flow_used": "error",
                "tools_executed": [],
                "next_suggested_actions": []
            }
    
    def _get_current_profile(self, client_id: str) -> Dict[str, Any]:
        """Get current complete profile for the client"""
        try:
            from sqlalchemy import text
            
            # Get business UUID
            business_uuid_query = text("SELECT id FROM businesses WHERE business_id = :business_id")
            business_result = self.db.execute(business_uuid_query, {"business_id": self.business_id}).fetchone()
            
            if not business_result:
                return {}
            
            business_uuid = business_result[0]
            
            # Get profile
            lead_query = text("""
                SELECT profile_json FROM visa_leads 
                WHERE business_id = :business_uuid AND id = :client_id
            """)
            lead_result = self.db.execute(lead_query, {
                "business_uuid": business_uuid,
                "client_id": client_id
            }).fetchone()
            
            if lead_result and lead_result[0]:
                return json.loads(lead_result[0])
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting profile: {e}")
            return {}
    
    def _generate_contextual_ai_response(self, message: str, intent: str, profile: Dict, 
                                       profile_delta: Dict, chat_history: List[Dict]) -> str:
        """
        Generate natural AI response based on context
        """
        try:
            # Build contextual prompt based on intent and profile
            prompt = self._build_contextual_prompt(message, intent, profile, profile_delta, chat_history)
            
            # Use direct synchronous MIA call (same as working restaurant service)
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={
                    "message": prompt,
                    "max_tokens": 80,  # Much shorter responses
                    "temperature": 0.7
                },
                timeout=30
            )
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data.get("response", "")
                
                if ai_response and len(ai_response.strip()) > 10:
                    logger.info(f"✅ AI response successful for {intent}")
                    return ai_response.strip()
            
            # Fallback to contextual template if AI fails
            return self._get_contextual_fallback(intent, profile, profile_delta)
            
        except Exception as e:
            logger.error(f"❌ AI generation failed: {e}")
            return self._get_contextual_fallback(intent, profile, profile_delta)
    
    def _build_contextual_prompt(self, message: str, intent: str, profile: Dict, 
                               profile_delta: Dict, chat_history: List[Dict]) -> str:
        """
        Build contextual prompt for AI based on conversation state
        """
        prompt = f"""You are Maya, a professional visa consultant at GSI Bali Agency helping people get visas to visit INDONESIA.

CONVERSATION CONTEXT:
- Intent: {intent}
- Current message: "{message}"
- IMPORTANT: Customer wants to visit INDONESIA (not their home country)

CUSTOMER PROFILE:"""
        
        if profile:
            if profile.get("nationality_iso2"):
                prompt += f"\n- Nationality: {profile['nationality_iso2']}"
            if profile.get("purpose"):
                prompt += f"\n- Purpose: {profile['purpose']}"
            if profile.get("intended_stay_days"):
                days = profile["intended_stay_days"]
                prompt += f"\n- Duration: {days} days"
        
        if profile_delta:
            prompt += f"\nNEW INFO THIS MESSAGE: {profile_delta}"
        
        # Add conversation progression guidance
        prompt += f"""

RESPONSE GUIDELINES FOR {intent.upper()}:"""
        
        if intent == "greeting":
            prompt += """
- Warm welcome
- Ask for 1-2 key pieces of info (nationality, purpose, OR duration)
- Keep it short and friendly"""
        
        elif intent == "provide_profile_data":
            prompt += """
- Acknowledge the new information provided
- If you have enough info (nationality + purpose + duration), give a specific recommendation
- If missing key info, ask for 1 missing piece only
- Be encouraging and show progress"""
        
        elif intent == "ask_recommendation":
            if profile.get("nationality_iso2") and profile.get("purpose"):
                prompt += """
- Give a specific visa recommendation based on their profile
- Explain why it's suitable for their situation
- Ask if they want to know requirements or costs"""
            else:
                prompt += """
- Need more info first - ask for missing nationality, purpose, or duration
- Explain why you need this info to give the best recommendation"""
        
        elif intent == "ask_requirements":
            prompt += """
- List specific requirements for their situation
- Be practical and actionable
- Mention next steps"""
        
        elif intent == "ask_price":
            prompt += """
- Provide pricing information
- Mention what's included
- Ask if they want to proceed"""
        
        prompt += """

CRITICAL RESPONSE RULES:
- MAXIMUM 2 SENTENCES ONLY - NO EXCEPTIONS
- NO LISTS OR NUMBERED POINTS
- ONE MAIN MESSAGE PER RESPONSE
- CONTEXTUAL (reference their specific situation visiting INDONESIA)
- PROGRESSIVE (build on what you already know, don't repeat)
- NATURAL but CONCISE

Generate a helpful response as Maya:"""
        
        return prompt
    
    def _get_contextual_fallback(self, intent: str, profile: Dict, profile_delta: Dict) -> str:
        """
        Contextual fallback responses when AI fails
        """
        nationality = profile.get("nationality_iso2", "")
        purpose = profile.get("purpose", "")
        duration = profile.get("intended_stay_days", 0)
        
        if intent == "greeting":
            return "Hi! I'm Maya from GSI Bali Agency. I'd love to help with your Indonesia visa! What brings you to Indonesia and where are you from?"
        
        elif intent == "provide_profile_data":
            if profile_delta.get("nationality_iso2") and profile_delta.get("purpose"):
                return f"Perfect! {nationality} travelers for {purpose} - I can definitely help with that. How long are you planning to stay?"
            elif nationality and purpose and duration:
                days_text = f"{duration} days" if duration < 30 else f"{duration//30} months"
                return f"Excellent! For {nationality} travelers visiting for {purpose} for {days_text}, I recommend the Tourist Visa (B211A). Would you like to know the requirements?"
            else:
                return "Thanks for that information! To give you the best visa recommendation, could you tell me your nationality and travel purpose?"
        
        elif intent == "ask_recommendation":
            if nationality and purpose:
                return f"For {nationality} travelers visiting for {purpose}, I recommend the Tourist Visa (B211A). It's perfect for your needs! Would you like to know the requirements or costs?"
            else:
                return "I'd love to recommend the perfect visa! Could you tell me your nationality and what's bringing you to Indonesia?"
        
        elif intent == "ask_requirements":
            return "For the Tourist Visa (B211A), you'll need: valid passport (6+ months), return ticket, and proof of accommodation. Would you like help with the application process?"
        
        elif intent == "ask_price":
            return "The Tourist Visa (B211A) costs $35 USD plus our service fee. This includes the visa and our full support. Ready to get started?"
        
        else:
            return "I'm here to help with your Indonesia visa needs! What specific information would you like to know?"
    
    def _get_next_actions(self, intent: str, profile: Dict) -> List[str]:
        """
        Suggest next actions based on current state
        """
        nationality = profile.get("nationality_iso2")
        purpose = profile.get("purpose")
        duration = profile.get("intended_stay_days")
        
        if not nationality:
            return ["ask_nationality"]
        elif not purpose:
            return ["ask_purpose"]
        elif not duration:
            return ["ask_duration"]
        elif intent in ["greeting", "provide_profile_data"]:
            return ["give_recommendation"]
        elif intent == "ask_recommendation":
            return ["ask_requirements", "ask_price"]
        elif intent == "ask_requirements":
            return ["ask_price", "start_application"]
        elif intent == "ask_price":
            return ["start_application"]
        else:
            return ["continue_conversation"]


def hybrid_visa_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Main entry point for hybrid visa chat service
    """
    try:
        # Get chat history for context
        from services.visa_chat_service_full_flows import get_chat_history_sql, save_chat_message_sql
        
        chat_history = get_chat_history_sql(db, req.client_id, req.restaurant_id)
        
        # Initialize hybrid service
        hybrid_service = HybridVisaService(db, req.restaurant_id)
        
        # Process message through hybrid system
        result = hybrid_service.process_message(
            message=req.message,
            client_id=req.client_id,
            chat_history=chat_history
        )
        
        # Save conversation to database
        save_chat_message_sql(db, req.client_id, req.restaurant_id, req.message, "client")
        save_chat_message_sql(db, req.client_id, req.restaurant_id, result["answer"], "ai")
        
        logger.info(f"🎯 Hybrid visa service completed for {req.restaurant_id}")
        
        return ChatResponse(
            answer=result["answer"],
            response_id=result.get("flow_used", "hybrid"),
            confidence_score=0.9
        )
        
    except Exception as e:
        logger.error(f"Error in hybrid visa chat service: {str(e)}")
        return ChatResponse(
            answer="I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa inquiry.",
            response_id="error",
            confidence_score=0.0
        )
