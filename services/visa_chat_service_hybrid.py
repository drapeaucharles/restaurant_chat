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
            
            # Get chat history from database if not provided (like restaurant service does)
            if not chat_history:
                chat_history = self._get_chat_history_from_db(client_id)
                logger.info(f"🔍 DEBUG: Retrieved chat history from DB: {len(chat_history)} messages")
            else:
                logger.info(f"🔍 DEBUG: Using provided chat history: {len(chat_history)} messages")
            
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
            logger.info(f"🔍 DEBUG: Current profile: {current_profile}")
            
            # Step 4: Generate AI response based on intent and context
            ai_response = self._generate_contextual_ai_response(
                message=message,
                intent=intent,
                profile=current_profile,
                profile_delta=profile_delta,
                chat_history=chat_history
            )
            
            # Add debug info to response for real-time debugging
            debug_info = f"""
[DEBUG INFO]
- Intent: {intent}
- Profile: {current_profile}
- ProfileDelta: {profile_delta}
- ChatHistory: {len(chat_history)} messages
- AI Response: {'SUCCESS' if ai_response else 'FAILED'}
- Response Length: {len(ai_response) if ai_response else 0}
"""
            
            return {
                "answer": ai_response + debug_info,
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
                # Handle both string and dict formats
                profile_data = lead_result[0]
                if isinstance(profile_data, str):
                    return json.loads(profile_data)
                elif isinstance(profile_data, dict):
                    return profile_data
                else:
                    logger.warning(f"Unexpected profile data type: {type(profile_data)}")
                    return {}
            
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
            logger.info(f"🤖 AI PROMPT DEBUG: Intent={intent}, Profile={profile}, ProfileDelta={profile_delta}")
            logger.info(f"🤖 AI PROMPT LENGTH: {len(prompt)} characters")
            
            # Use direct synchronous MIA call (same as working restaurant service)
            logger.info(f"🚀 Making MIA request to: {MIA_BACKEND_URL}/chat")
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={
                    "message": prompt,
                    "max_tokens": 80,  # Much shorter responses
                    "temperature": 0.7
                },
                timeout=30
            )
            logger.info(f"📡 MIA Response Status: {response.status_code}")
            
            if response.status_code == 200:
                response_data = response.json()
                ai_response = response_data.get("response", "")
                logger.info(f"📥 MIA Response Data: {response_data}")
                logger.info(f"📝 AI Response Raw: '{ai_response}'")
                
                if ai_response and len(ai_response.strip()) > 10:
                    logger.info(f"✅ AI response successful for {intent}: '{ai_response[:50]}...'")
                    return ai_response.strip()
                else:
                    logger.warning(f"⚠️ AI response too short or empty: '{ai_response}' - using fallback")
            else:
                logger.warning(f"⚠️ MIA request failed with status {response.status_code} - using fallback")
                logger.warning(f"📄 Response text: {response.text}")
            
            # Fallback to contextual template if AI fails
            logger.info(f"🔄 Using contextual fallback for {intent}")
            fallback_response = self._get_contextual_fallback(intent, profile, profile_delta)
            
            # Add debug info to fallback response
            debug_info = f"""
[DEBUG INFO - FALLBACK]
- Intent: {intent}
- Profile: {profile}
- ProfileDelta: {profile_delta}
- AI Call: FAILED
- Using: Fallback Response
"""
            return fallback_response + debug_info
            
        except Exception as e:
            logger.error(f"❌ AI generation failed: {e}")
            fallback_response = self._get_contextual_fallback(intent, profile, profile_delta)
            
            # Add debug info to exception fallback
            debug_info = f"""
[DEBUG INFO - EXCEPTION]
- Intent: {intent}
- Profile: {profile}
- ProfileDelta: {profile_delta}
- Error: {str(e)}
- Using: Exception Fallback
"""
            return fallback_response + debug_info
    
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
- Warm welcome and ask "How can I help you?"
- Don't ask for specific info immediately
- Let them tell you what they need"""
        
        elif intent == "provide_profile_data":
            prompt += """
- Acknowledge the new information provided
- Check what info you already have vs what's missing
- If you have nationality + purpose + duration, give specific recommendation
- If missing info, ask for ONLY the missing piece (don't repeat what you already know)
- Show progress and be encouraging"""
        
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
            return "Hello! I'm Maya from GSI Bali Agency. How can I help you with your Indonesia visa today?"
        
        elif intent == "provide_profile_data":
            if profile_delta.get("nationality_iso2") and profile_delta.get("purpose"):
                return f"Perfect! {nationality} travelers for {purpose} - I can definitely help with that. How long are you planning to stay?"
            elif nationality and purpose and duration:
                return f"Perfect! For {nationality} travelers, I recommend the Tourist Visa (B211A). Would you like to know the requirements?"
            else:
                return "Thanks! Could you tell me your nationality and travel purpose?"
        
        elif intent == "ask_recommendation":
            if nationality and purpose:
                return f"For {nationality} travelers, I recommend the Tourist Visa (B211A). Would you like to know the requirements?"
            else:
                return "I'd love to help! Could you tell me your nationality and travel purpose?"
        
        elif intent == "ask_requirements":
            return "You'll need: valid passport (6+ months), return ticket, and proof of accommodation. Ready to apply?"
        
        elif intent == "ask_price":
            return "The Tourist Visa costs $35 USD plus service fee. Ready to get started?"
        
        else:
            return "I'm here to help with your Indonesia visa! What would you like to know?"
    
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
        logger.info(f"🚀 HYBRID SERVICE ENTRY: Processing message '{req.message[:50]}...' for {req.restaurant_id}")
        
        # Add immediate debug response to confirm we're being called
        debug_response = f"[HYBRID SERVICE CALLED] Message: {req.message[:50]}..."
        logger.info(f"🔍 DEBUG: {debug_response}")
        
        # Get chat history for context
        from services.visa_chat_service_full_flows import get_chat_history_sql, save_chat_message_sql
        
        logger.info(f"🔍 DEBUG: Getting chat history for client {req.client_id}")
        chat_history = get_chat_history_sql(db, req.client_id, req.restaurant_id)
        logger.info(f"✅ DEBUG: Got {len(chat_history)} chat history messages")
        
        # Initialize hybrid service
        logger.info(f"🔍 DEBUG: Initializing HybridVisaService for {req.restaurant_id}")
        hybrid_service = HybridVisaService(db, req.restaurant_id)
        logger.info(f"✅ DEBUG: HybridVisaService initialized successfully")
        
        # Process message through hybrid system
        logger.info(f"🔍 DEBUG: Processing message through hybrid system")
        result = hybrid_service.process_message(
            message=req.message,
            client_id=req.client_id,
            chat_history=chat_history
        )
        logger.info(f"✅ DEBUG: Hybrid processing completed, answer: '{result['answer'][:50]}...'")
        
        # Save conversation to database
        save_chat_message_sql(db, req.client_id, req.restaurant_id, req.message, "client")
        save_chat_message_sql(db, req.client_id, req.restaurant_id, result["answer"], "ai")
        
        logger.info(f"🎯 Hybrid visa service completed for {req.restaurant_id}")
        
        return ChatResponse(
            answer=result["answer"] + f"\n\n[HYBRID SERVICE CONFIRMED]",
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
