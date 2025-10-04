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
            
            # Step 1.5: AI-POWERED INFORMATION EXTRACTION for multi-language support
            # Always try AI extraction for ALL languages (not just when orchestrator fails)
            logger.info(f"🤖 Running AI extraction for multi-language support...")
            ai_extracted = self._extract_info_with_ai(message)
            if ai_extracted:
                # Merge AI extracted data with orchestrator data (AI takes precedence for missing fields)
                for key, value in ai_extracted.items():
                    if key not in profile_delta and value:
                        profile_delta[key] = value
                        logger.info(f"✅ AI added missing field {key}: {value}")
                logger.info(f"✅ AI extracted data: {ai_extracted}")
            else:
                logger.info(f"⚠️ AI extraction returned no data")
            
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
            
            # Add comprehensive debug info to response for real-time debugging
            debug_info = f"""
[DEBUG INFO]
- Intent: {intent}
- Profile: {current_profile}
- ProfileDelta: {profile_delta}
- ChatHistory: {len(chat_history)} messages
- AI Response: {'SUCCESS' if ai_response else 'FAILED'}
- Response Length: {len(ai_response) if ai_response else 0}
- Orchestrator Extracted: {router_result.get('profile_delta', {})}
- AI Enhanced: {ai_extracted if 'ai_extracted' in locals() else 'N/A'}
- Extraction Status: {'AI_ENHANCED' if 'ai_extracted' in locals() and ai_extracted else 'ORCHESTRATOR_ONLY'}
- Message: '{message[:50]}...'
- Language Detection: Working
- Multi-Language Support: Active
"""
            
            return {
                "answer": ai_response + debug_info,
                "flow_used": f"hybrid_{intent}",
                "tools_executed": ["profile_extraction", "ai_generation"],
                "next_suggested_actions": self._get_next_actions(intent, current_profile)
            }
        
        except Exception as e:
            logger.error(f"❌ Hybrid service error: {e}")
            
            # Add debug info to error response
            error_debug_info = f"""
[DEBUG INFO - ERROR]
- Error: {str(e)}
- Intent: {intent if 'intent' in locals() else 'UNKNOWN'}
- Profile: {current_profile if 'current_profile' in locals() else 'UNKNOWN'}
- ProfileDelta: {profile_delta if 'profile_delta' in locals() else 'UNKNOWN'}
- Message: '{message[:50] if 'message' in locals() else 'UNKNOWN'}...'
- Extraction Status: ERROR
"""
            
            return {
                "answer": "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa inquiry." + error_debug_info,
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
                    "max_tokens": 35,  # Very short responses - enforce 120 char limit
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
            
            # Return clean fallback response without debug info
            return fallback_response
            
        except Exception as e:
            logger.error(f"❌ AI generation failed: {e}")
            fallback_response = self._get_contextual_fallback(intent, profile, profile_delta)
            
            # Return clean exception fallback without debug info
            return fallback_response
    
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

MULTI-LANGUAGE INTELLIGENCE RULES:
- DETECT LANGUAGE: Identify the language of their message
- RESPOND IN SAME LANGUAGE: Always respond in the same language they used
- SUPPORTED LANGUAGES: English, Indonesian (Bahasa Indonesia), Spanish, French, German, Japanese, Korean, Chinese, Arabic, Portuguese, Italian, Dutch, Russian, Thai, Vietnamese, Malay
- LANGUAGE EXAMPLES:
  * English: "Hello, I need a visa" → Respond in English
  * Indonesian: "Halo, saya butuh visa" → Respond in Indonesian
  * Spanish: "Hola, necesito una visa" → Respond in Spanish
- MAINTAIN PROFESSIONALISM: Use appropriate formal/informal tone based on language
- CULTURAL AWARENESS: Adapt response style to cultural norms of the language

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
        
        # Add profile validation rules
        prompt += """

PROFILE VALIDATION RULES:
- DURATION VALIDATION: If duration > 365 days, suggest this might be for long-term residence
- DURATION VALIDATION: If duration > 10000 days, this seems unreasonable - ask for clarification
- PURPOSE VALIDATION: Ensure purpose matches their stated intentions
- NATIONALITY VALIDATION: Confirm nationality is clear and valid
- CONSISTENCY CHECK: Don't change purpose without explicit user request
- VISA TYPE VALIDATION: KITAS is for long-term residence (1+ years), NOT for short tourism
- VISA TYPE VALIDATION: B211A allows 30 days extendable to 60 days, NOT 180 days
- VISA TYPE VALIDATION: E-KIT is for 30 days extendable to 60 days, NOT longer"""
        
        # Add conversation progression guidance
        prompt += f"""

RESPONSE GUIDELINES FOR {intent.upper()}:"""
        
        if intent == "greeting":
            prompt += """
- CRITICAL GREETING RULES:
  * If no name in profile: Ask "What's your name?" 
  * If name exists: Say "Perfect [Name]! What can I do for you today?"
  * NEVER ask for nationality/purpose in greeting
  * Focus on name first, then let them tell you what they need
- Build rapport before gathering information"""
        
        elif intent == "provide_profile_data":
            prompt += """
- CONTEXT AWARENESS RULES:
  * NEVER ask for information already in the profile
  * Acknowledge what they just provided
  * Show what you know: "I now have your nationality (X), purpose (Y), duration (Z)"
  * Identify ONLY the missing piece needed for recommendation
  * If profile is complete (nationality + purpose + duration), give specific recommendation
  * If incomplete, ask for ONLY the missing piece with encouragement
- SMART FOLLOW-UP RULES:
  * Ask contextually relevant questions based on their visa type
  * For tourism: Ask about destinations, travel dates, accommodation
  * For business: Ask about company, meetings, business contacts
  * For education: Ask about institution, program, start date
  * For investment: Ask about investment amount, business type
- PROGRESS TRACKING: Show conversation progress clearly
- AVOID REPETITION: Don't ask for info you already have
- MULTI-LANGUAGE INFO EXTRACTION:
  * Extract nationality from ANY language (not just English)
  * Extract purpose from ANY language (tourism, business, education, etc.)
  * Extract duration from ANY language format
  * Use context clues to understand meaning regardless of language"""
        
        elif intent == "ask_recommendation":
            if profile.get("nationality_iso2") and profile.get("purpose"):
                # Get duration for specific rules
                duration = profile.get("intended_stay_days", 0)
                
                if duration > 365:
                    prompt += """
- CRITICAL DURATION RULE: Stay > 365 days = LONG-TERM RESIDENCE
- RECOMMEND: KITAS or VITAS (NOT B211A or E-KIT)
- KITAS allows 1+ years residence, perfect for long-term stays
- Include pricing: KITAS/VITAS (varies by type, typically IDR 3,000,000+)
- Explain this is for long-term residence, not tourism"""
                elif duration > 180:
                    prompt += """
- CRITICAL DURATION RULE: Stay > 180 days = EXTENDED STAY
- RECOMMEND: KITAS (long-term) or B211A with multiple extensions
- B211A allows 30 days + 2 extensions (30+60+60 = 150 days max)
- For 180+ days, KITAS is more appropriate than multiple extensions
- Include pricing: B211A (IDR 1,500,000), KITAS (varies)
- Explain extension limitations vs long-term visa benefits"""
                elif duration > 60:
                    prompt += """
- DURATION RULE: Stay > 60 days = NEEDS EXTENSION
- RECOMMEND: B211A (30 days extendable to 60) with extension plan
- E-KIT only allows 30 days extendable to 60 days max
- B211A is better for stays > 60 days
- Include pricing: B211A (IDR 1,500,000)
- Explain extension process and timing"""
                elif duration > 30:
                    prompt += """
- DURATION RULE: Stay 30-60 days = EXTENDABLE VISA
- RECOMMEND: B211A (30 days extendable to 60) or E-KIT (30 days extendable to 60)
- Both allow 30 days initial + 1 extension to 60 days
- E-KIT is cheaper (IDR 500,000), B211A more flexible (IDR 1,500,000)
- Include pricing and explain extension process"""
                else:
                    prompt += """
- DURATION RULE: Stay ≤ 30 days = SHORT STAY
- RECOMMEND: E-KIT (30 days) or B211A (30 days)
- E-KIT is perfect for short tourism (IDR 500,000)
- B211A if they need more flexibility (IDR 1,500,000)
- Include pricing and explain no extension needed"""
                
                prompt += """
- CRITICAL VISA TYPE ACCURACY:
  * KITAS = Long-term residence (1+ years), NOT for short tourism
  * B211A = 30 days extendable to 60 days, NOT 180 days
  * E-KIT = 30 days extendable to 60 days, NOT longer
- PERSONALIZED RECOMMENDATION FORMAT:
  * Use their name: "[Name], I recommend [Visa Type]"
  * Explain reasoning: "based on your [duration] stay for [purpose]"
  * Reference nationality: "knowing you're from [Country]"
  * Example: "Charles, I recommend E-KIT based on your 30-day tourism visit from Canada"
- Always match visa duration capacity to their intended stay
- Explain why this specific visa fits their situation
- Ask if they want requirements or costs"""
            else:
                prompt += """
- Need more info first - ask for missing nationality, purpose, or duration
- Explain why you need this info to give the best recommendation"""
        
        elif intent == "ask_requirements":
            prompt += """
- REQUIREMENTS INTELLIGENCE RULES:
  * Analyze their profile to determine visa type first
  * BASE REQUIREMENTS: Passport (6+ months), photo, application form, accommodation proof, return ticket
  * SPONSOR REQUIREMENTS: Required for B211A, B211B, KITAS, VITAS (not for E-KIT)
  * PURPOSE-SPECIFIC: Add requirements based on purpose (business letter, medical documents, etc.)
  * DURATION-SPECIFIC: Long-term visas may need additional financial proof
- TIMELINE EXPECTATIONS:
  * E-KIT: 1-3 business days processing
  * B211A/B211B: 3-5 business days processing
  * KITAS/VITAS: 7-14 business days processing
  * Always mention processing time when discussing requirements
- Provide requirements that match their specific visa recommendation
- Be practical and actionable
- Mention next steps"""
        
        elif intent == "ask_price":
            prompt += """
- PRICING INTELLIGENCE RULES:
  * Match pricing to their recommended visa type
  * STANDARD PRICING: E-KIT (IDR 500,000), B211A (IDR 1,500,000), B211B (IDR 1,500,000)
  * LONG-TERM PRICING: KITAS/VITAS (varies by type, typically IDR 3,000,000+)
  * EXPLAIN VALUE: Mention what's included (processing, government fees, support)
  * COMPARISON: If multiple options, explain cost differences
  * ALWAYS INCLUDE PRICING: When recommending visas, always mention cost
- Be transparent about pricing
- Ask if they want to proceed"""
        
        prompt += """
        
        CONVERSATION INTELLIGENCE RULES:
        - CONSISTENCY: Similar scenarios should get similar response patterns
        - PROGRESSION: Build logically on previous conversation
        - PERSONALIZATION: Reference their specific nationality, purpose, duration
        - EFFICIENCY: Don't repeat information already provided
        - CLARITY: Be specific about visa types and requirements
        - MEMORY: Always reference what you already know about them
        - CONTEXT: Use chat history to understand conversation flow
        - ERROR HANDLING: If unclear request, ask for clarification politely
        - EDGE CASES: Handle unusual requests gracefully (multiple purposes, extreme durations, etc.)
        
        CRITICAL RESPONSE RULES:
        - MAXIMUM 1-2 SENTENCES ONLY - NO EXCEPTIONS
        - MAXIMUM 120 CHARACTERS TOTAL - ENFORCE STRICTLY
        - NO LISTS OR NUMBERED POINTS
        - ONE MAIN MESSAGE PER RESPONSE
        - ONE QUESTION AT A TIME - NEVER ASK MULTIPLE QUESTIONS
        - CONTEXTUAL (reference their specific situation visiting INDONESIA)
        - PROGRESSIVE (build on what you already know, don't repeat)
        - NATURAL but EXTREMELY CONCISE
        
        Generate a helpful response as Maya:"""
        
        return prompt
    
    def _extract_info_with_ai(self, message: str) -> Dict[str, Any]:
        """Use AI to extract nationality, purpose, and duration from ANY language"""
        try:
            import requests
            from config import MIA_BACKEND_URL
            
            extraction_prompt = f"""Extract visa information from this message in ANY language:

MESSAGE: "{message}"

Extract and return ONLY a JSON object with:
- nationality_iso2: ISO2 country code (e.g., "US", "CA", "FR", "DE", "JP")
- purpose: one of ["tourism", "business", "education", "work", "investment", "retirement", "family_visit"]
- intended_stay_days: number of days (extract from any time format)
- client_name: extracted name if mentioned

EXAMPLES:
- "Je suis français et je veux visiter Bali pendant 30 jours" → {{"nationality_iso2": "FR", "purpose": "tourism", "intended_stay_days": 30}}
- "Soy argentino, vengo por negocios por 2 semanas" → {{"nationality_iso2": "AR", "purpose": "business", "intended_stay_days": 14}}
- "私は日本人で、観光で60日間滞在したい" → {{"nationality_iso2": "JP", "purpose": "tourism", "intended_stay_days": 60}}

Return ONLY valid JSON, no other text:"""

            # Call MIA backend directly to avoid circular calls
            response = requests.post(
                f"{MIA_BACKEND_URL}/chat",
                json={
                    "message": extraction_prompt,
                    "max_tokens": 100,
                    "temperature": 0.3
                },
                timeout=15
            )
            
            if response.status_code == 200:
                ai_response = response.json().get("response", "").strip()
                # Try to parse JSON from AI response
                import json
                import re
                
                # Look for JSON pattern in response
                json_match = re.search(r'\{[^}]*\}', ai_response)
                if json_match:
                    extracted_data = json.loads(json_match.group())
                    logger.info(f"🤖 AI extracted: {extracted_data}")
                    return extracted_data
                    
        except Exception as e:
            logger.warning(f"AI extraction failed: {e}")
            
        return {}

    def _get_contextual_fallback(self, intent: str, profile: Dict, profile_delta: Dict) -> str:
        """
        Contextual fallback responses when AI fails
        """
        nationality = profile.get("nationality_iso2", "")
        purpose = profile.get("purpose", "")
        duration = profile.get("intended_stay_days", 0)
        
        if intent == "greeting":
            name = profile.get("client_name", "")
            if name:
                return f"Perfect {name}! What can I do for you today?"
            else:
                return "Hello! I'm Maya from GSI Bali Agency. What's your name?"
        
        elif intent == "provide_profile_data":
            name = profile.get("client_name", "")
            if profile_delta.get("client_name"):
                return f"Nice to meet you {profile_delta['client_name']}! What's your nationality and the purpose of your visit to Indonesia?"
            elif profile_delta.get("nationality_iso2") and profile_delta.get("purpose"):
                greeting = f"Perfect {name}! " if name else "Perfect! "
                return f"{greeting}{nationality} travelers for {purpose} - I can definitely help with that. How long are you planning to stay?"
            elif nationality and purpose and duration:
                greeting = f"Perfect {name}! " if name else "Perfect! "
                return f"{greeting}For {nationality} travelers, I recommend the Tourist Visa (B211A). Would you like to know the requirements?"
            else:
                greeting = f"Thanks {name}! " if name else "Thanks! "
                return f"{greeting}Could you tell me your nationality and travel purpose?"
        
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
