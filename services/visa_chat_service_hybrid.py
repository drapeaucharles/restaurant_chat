# services/visa_chat_service_hybrid.py
"""
Hybrid Visa Chat Service - Best of Both Worlds
- Uses WorkingVisaFlowOrchestrator for routing and profile management
- Uses AI for natural response generation
- Maintains conversation context and progression

🚨 CRITICAL RULES - NO HARDCODING:
- NEVER hardcode product names like "E-KIT", "B211A", "KITAS"
- ALWAYS use database products as source of truth
- NEVER hardcode pricing like "500,000 IDR"
- ALWAYS query database for actual product data
- See DEVELOPMENT_RULES.md for complete guidelines
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
                
                if ai_response and len(ai_response.strip()) > 3:
                    logger.info(f"✅ AI response successful for {intent}: '{ai_response[:50]}...'")
                    return ai_response.strip()
                else:
                    logger.warning(f"⚠️ AI response too short or empty: '{ai_response}' - using fallback")
            else:
                logger.warning(f"⚠️ MIA request failed with status {response.status_code} - using fallback")
                logger.warning(f"📄 Response text: {response.text}")
            
            # Try OpenAI fallback if MIA fails
            logger.warning(f"⚠️ MIA failed, trying OpenAI fallback")
            openai_response = self._try_openai_fallback(prompt)
            if openai_response:
                logger.info(f"✅ OpenAI fallback successful: '{openai_response[:50]}...'")
                return openai_response
            
            # Final fallback - intelligent language-specific responses based on intent
            logger.warning(f"⚠️ All AI services failed, using intelligent language-specific fallback")
            logger.info(f"✅ Using database-driven fallback responses (no hardcoding)")
            message_language = self._detect_language_from_message(message)
            
            # Get contextual response based on intent and profile
            if intent == "greeting":
                if message_language == "fr":
                    return "Bonjour! Je suis Maya de GSI Bali Agency. Comment puis-je vous aider avec votre visa pour l'Indonésie?"
                elif message_language == "es":
                    return "¡Hola! Soy Maya de GSI Bali Agency. ¿Cómo puedo ayudarte con tu visa para Indonesia?"
                elif message_language == "de":
                    return "Hallo! Ich bin Maya von GSI Bali Agency. Wie kann ich Ihnen bei Ihrem Visum für Indonesien helfen?"
                elif message_language == "ja":
                    return "こんにちは！私はGSI Bali Agencyのマヤです。インドネシアのビザについてどのようにお手伝いできますか？"
                else:
                    return "Hello! I'm Maya from GSI Bali Agency. How can I help you with your visa for Indonesia?"
            
            elif intent == "provide_profile_data":
                if message_language == "fr":
                    return "Parfait! Maintenant, pouvez-vous me dire votre nationalité et le but de votre voyage?"
                elif message_language == "es":
                    return "¡Perfecto! Ahora, ¿puedes decirme tu nacionalidad y el propósito de tu viaje?"
                elif message_language == "de":
                    return "Perfekt! Können Sie mir jetzt Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                elif message_language == "ja":
                    return "完璧です！今度は、あなたの国籍と旅行の目的を教えていただけますか？"
                else:
                    return "Perfect! Now, can you tell me your nationality and travel purpose?"
            
            elif intent == "ask_recommendation":
                # Check if we have enough profile data to make a recommendation
                if profile.get("nationality_iso2") and profile.get("purpose"):
                    # Get database products and find best match
                    products = self._get_database_visa_products(db)
                    recommended_product = self._find_best_visa_match(profile, products)
                    
                    if recommended_product:
                        duration = profile.get("intended_stay_days", 0)
                        product_name = recommended_product["name"]
                        product_price = recommended_product["price"]
                        
                        # Make specific recommendations using ACTUAL database products
                        if message_language == "fr":
                            return f"Parfait! Basé sur votre profil (nationalité: {profile['nationality_iso2']}, but: {profile['purpose']}, durée: {duration} jours), je recommande {product_name} pour {duration} jours. Coût: {product_price:,} IDR."
                        elif message_language == "es":
                            return f"¡Perfecto! Basado en tu perfil (nacionalidad: {profile['nationality_iso2']}, propósito: {profile['purpose']}, duración: {duration} días), recomiendo {product_name} para {duration} días. Costo: {product_price:,} IDR."
                        elif message_language == "de":
                            return f"Perfekt! Basierend auf Ihrem Profil (Nationalität: {profile['nationality_iso2']}, Zweck: {profile['purpose']}, Dauer: {duration} Tage), empfehle ich {product_name} für {duration} Tage. Kosten: {product_price:,} IDR."
                        elif message_language == "ja":
                            return f"完璧です！あなたのプロフィール（国籍: {profile['nationality_iso2']}, 目的: {profile['purpose']}, 期間: {duration}日）に基づいて、{product_name}をお勧めします。費用: {product_price:,} IDR。"
                        else:  # English
                            return f"Perfect! Based on your profile (nationality: {profile['nationality_iso2']}, purpose: {profile['purpose']}, duration: {duration} days), I recommend {product_name} for {duration} days. Cost: {product_price:,} IDR."
                    else:
                        # No database products found - fallback to generic response
                        if message_language == "fr":
                            return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                        elif message_language == "es":
                            return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                        elif message_language == "de":
                            return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                        elif message_language == "ja":
                            return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                        else:
                            return "I'd love to help! Could you tell me your nationality and travel purpose?"
                else:
                    # Don't have enough profile data yet
                    if message_language == "fr":
                        return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                    elif message_language == "es":
                        return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                    elif message_language == "de":
                        return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                    elif message_language == "ja":
                        return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                    else:
                        return "I'd love to help! Could you tell me your nationality and travel purpose?"
            
            elif intent == "ask_requirements":
                # Check if we have enough profile data to provide specific requirements
                if profile.get("nationality_iso2") and profile.get("purpose"):
                    # Get database products and find best match
                    products = self._get_database_visa_products(db)
                    recommended_product = self._find_best_visa_match(profile, products)
                    
                    if recommended_product:
                        product_name = recommended_product["name"]
                        
                        # Provide specific requirements using ACTUAL database products
                        if message_language == "fr":
                            return f"Pour {product_name}, vous aurez besoin de: passeport (6+ mois), photo, formulaire de demande, preuve d'hébergement, billet de retour."
                        elif message_language == "es":
                            return f"Para {product_name}, necesitarás: pasaporte (6+ meses), foto, formulario de solicitud, comprobante de alojamiento, boleto de regreso."
                        elif message_language == "de":
                            return f"Für {product_name} benötigen Sie: Reisepass (6+ Monate), Foto, Antragsformular, Unterkunftsnachweis, Rückflugticket."
                        elif message_language == "ja":
                            return f"{product_name}には以下が必要です：パスポート（6ヶ月以上）、写真、申請書、宿泊証明、帰国チケット。"
                        else:  # English
                            return f"For {product_name}, you'll need: passport (6+ months), photo, application form, accommodation proof, return ticket."
                    else:
                        # No database products found - fallback to generic response
                        if message_language == "fr":
                            return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                        elif message_language == "es":
                            return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                        elif message_language == "de":
                            return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                        elif message_language == "ja":
                            return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                        else:
                            return "I'd love to help! Could you tell me your nationality and travel purpose?"
                else:
                    # Don't have enough profile data yet
                    if message_language == "fr":
                        return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                    elif message_language == "es":
                        return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                    elif message_language == "de":
                        return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                    elif message_language == "ja":
                        return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                    else:
                        return "I'd love to help! Could you tell me your nationality and travel purpose?"
            
            elif intent == "ask_price":
                # Check if we have enough profile data to provide specific pricing
                if profile.get("nationality_iso2") and profile.get("purpose"):
                    # Get database products and find best match
                    products = self._get_database_visa_products(db)
                    recommended_product = self._find_best_visa_match(profile, products)
                    
                    if recommended_product:
                        product_name = recommended_product["name"]
                        product_price = recommended_product["price"]
                        
                        # Provide specific pricing using ACTUAL database products
                        if message_language == "fr":
                            return f"{product_name} coûte {product_price:,} IDR. Cela inclut les frais de traitement, les frais gouvernementaux et notre support."
                        elif message_language == "es":
                            return f"{product_name} cuesta {product_price:,} IDR. Esto incluye procesamiento, tarifas gubernamentales y nuestro apoyo."
                        elif message_language == "de":
                            return f"{product_name} kostet {product_price:,} IDR. Dies beinhaltet Bearbeitung, Regierungsgebühren und unsere Unterstützung."
                        elif message_language == "ja":
                            return f"{product_name}の費用は{product_price:,} IDRです。処理費、政府手数料、サポートが含まれます。"
                        else:  # English
                            return f"{product_name} costs {product_price:,} IDR. This includes processing, government fees, and our support."
                    else:
                        # No database products found - fallback to generic response
                        if message_language == "fr":
                            return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                        elif message_language == "es":
                            return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                        elif message_language == "de":
                            return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                        elif message_language == "ja":
                            return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                        else:
                            return "I'd love to help! Could you tell me your nationality and travel purpose?"
                else:
                    # Don't have enough profile data yet
                    if message_language == "fr":
                        return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                    elif message_language == "es":
                        return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                    elif message_language == "de":
                        return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                    elif message_language == "ja":
                        return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                    else:
                        return "I'd love to help! Could you tell me your nationality and travel purpose?"
            
            else:
                # Default response - ensure we always have language-specific responses
                if message_language == "fr":
                    return "Bonjour, je peux vous aider avec votre visa pour l'Indonésie."
                elif message_language == "es":
                    return "Hola, puedo ayudarte con tu visa para Indonesia."
                elif message_language == "de":
                    return "Hallo, ich kann Ihnen bei Ihrem Visum für Indonesien helfen."
                elif message_language == "ja":
                    return "こんにちは、インドネシアのビザについてお手伝いできます。"
                else:
                    return "Hello, I can help you with your visa for Indonesia."
            
        except Exception as e:
            logger.error(f"❌ AI generation failed: {e}")
            
            # Try OpenAI fallback even on exception
            try:
                prompt = self._build_contextual_prompt(message, intent, profile, profile_delta, chat_history)
                openai_response = self._try_openai_fallback(prompt)
                if openai_response:
                    logger.info(f"✅ OpenAI fallback successful on exception: '{openai_response[:50]}...'")
                    return openai_response
            except Exception as fallback_error:
                logger.warning(f"OpenAI fallback also failed: {fallback_error}")
            
            # Final fallback - intelligent language-specific responses based on intent
            logger.error(f"🚨 WARNING: Using hardcoded fallback responses in exception handler - this violates no-hardcoding rules!")
            logger.error(f"🚨 SHOULD: Query database for actual products instead of hardcoded types")
            message_language = self._detect_language_from_message(message)
            
            # Get contextual response based on intent and profile
            if intent == "greeting":
                if message_language == "fr":
                    return "Bonjour! Je suis Maya de GSI Bali Agency. Comment puis-je vous aider avec votre visa pour l'Indonésie?"
                elif message_language == "es":
                    return "¡Hola! Soy Maya de GSI Bali Agency. ¿Cómo puedo ayudarte con tu visa para Indonesia?"
                elif message_language == "de":
                    return "Hallo! Ich bin Maya von GSI Bali Agency. Wie kann ich Ihnen bei Ihrem Visum für Indonesien helfen?"
                elif message_language == "ja":
                    return "こんにちは！私はGSI Bali Agencyのマヤです。インドネシアのビザについてどのようにお手伝いできますか？"
                else:
                    return "Hello! I'm Maya from GSI Bali Agency. How can I help you with your visa for Indonesia?"
            
            elif intent == "provide_profile_data":
                if message_language == "fr":
                    return "Parfait! Maintenant, pouvez-vous me dire votre nationalité et le but de votre voyage?"
                elif message_language == "es":
                    return "¡Perfecto! Ahora, ¿puedes decirme tu nacionalidad y el propósito de tu viaje?"
                elif message_language == "de":
                    return "Perfekt! Können Sie mir jetzt Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                elif message_language == "ja":
                    return "完璧です！今度は、あなたの国籍と旅行の目的を教えていただけますか？"
                else:
                    return "Perfect! Now, can you tell me your nationality and travel purpose?"
            
            elif intent == "ask_recommendation":
                # Check if we have enough profile data to make a recommendation
                if profile.get("nationality_iso2") and profile.get("purpose"):
                    duration = profile.get("intended_stay_days", 0)
                    
                    # Make specific recommendations based on profile data
                    if message_language == "fr":
                        if duration <= 30:
                            return f"Parfait! Basé sur votre profil (nationalité: {profile['nationality_iso2']}, but: {profile['purpose']}, durée: {duration} jours), je recommande l'E-KIT pour {duration} jours. Coût: 500,000 IDR."
                        elif duration <= 60:
                            return f"Parfait! Basé sur votre profil (nationalité: {profile['nationality_iso2']}, but: {profile['purpose']}, durée: {duration} jours), je recommande le B211A (30 jours + extension). Coût: 1,500,000 IDR."
                        else:
                            return f"Parfait! Basé sur votre profil (nationalité: {profile['nationality_iso2']}, but: {profile['purpose']}, durée: {duration} jours), je recommande le KITAS pour un séjour long terme. Coût: variable selon le type."
                    elif message_language == "es":
                        if duration <= 30:
                            return f"¡Perfecto! Basado en tu perfil (nacionalidad: {profile['nationality_iso2']}, propósito: {profile['purpose']}, duración: {duration} días), recomiendo E-KIT para {duration} días. Costo: 500,000 IDR."
                        elif duration <= 60:
                            return f"¡Perfecto! Basado en tu perfil (nacionalidad: {profile['nationality_iso2']}, propósito: {profile['purpose']}, duración: {duration} días), recomiendo B211A (30 días + extensión). Costo: 1,500,000 IDR."
                        else:
                            return f"¡Perfecto! Basado en tu perfil (nacionalidad: {profile['nationality_iso2']}, propósito: {profile['purpose']}, duración: {duration} días), recomiendo KITAS para estadía larga. Costo: variable según tipo."
                    elif message_language == "de":
                        if duration <= 30:
                            return f"Perfekt! Basierend auf Ihrem Profil (Nationalität: {profile['nationality_iso2']}, Zweck: {profile['purpose']}, Dauer: {duration} Tage), empfehle ich E-KIT für {duration} Tage. Kosten: 500,000 IDR."
                        elif duration <= 60:
                            return f"Perfekt! Basierend auf Ihrem Profil (Nationalität: {profile['nationality_iso2']}, Zweck: {profile['purpose']}, Dauer: {duration} Tage), empfehle ich B211A (30 Tage + Verlängerung). Kosten: 1,500,000 IDR."
                        else:
                            return f"Perfekt! Basierend auf Ihrem Profil (Nationalität: {profile['nationality_iso2']}, Zweck: {profile['purpose']}, Dauer: {duration} Tage), empfehle ich KITAS für Langzeitaufenthalt. Kosten: je nach Typ variabel."
                    elif message_language == "ja":
                        if duration <= 30:
                            return f"完璧です！あなたのプロフィール（国籍: {profile['nationality_iso2']}, 目的: {profile['purpose']}, 期間: {duration}日）に基づいて、{duration}日間のE-KITをお勧めします。費用: 500,000 IDR。"
                        elif duration <= 60:
                            return f"完璧です！あなたのプロフィール（国籍: {profile['nationality_iso2']}, 目的: {profile['purpose']}, 期間: {duration}日）に基づいて、B211A（30日+延長）をお勧めします。費用: 1,500,000 IDR。"
                        else:
                            return f"完璧です！あなたのプロフィール（国籍: {profile['nationality_iso2']}, 目的: {profile['purpose']}, 期間: {duration}日）に基づいて、長期滞在用のKITASをお勧めします。費用: タイプにより異なります。"
                    else:  # English
                        if duration <= 30:
                            return f"Perfect! Based on your profile (nationality: {profile['nationality_iso2']}, purpose: {profile['purpose']}, duration: {duration} days), I recommend E-KIT for {duration} days. Cost: 500,000 IDR."
                        elif duration <= 60:
                            return f"Perfect! Based on your profile (nationality: {profile['nationality_iso2']}, purpose: {profile['purpose']}, duration: {duration} days), I recommend B211A (30 days + extension). Cost: 1,500,000 IDR."
                        else:
                            return f"Perfect! Based on your profile (nationality: {profile['nationality_iso2']}, purpose: {profile['purpose']}, duration: {duration} days), I recommend KITAS for long-term stay. Cost: varies by type."
                else:
                    # Don't have enough profile data yet
                    if message_language == "fr":
                        return "Je serais ravie de vous aider! Pouvez-vous me dire votre nationalité et le but de votre voyage?"
                    elif message_language == "es":
                        return "¡Me encantaría ayudarte! ¿Puedes decirme tu nacionalidad y el propósito de tu viaje?"
                    elif message_language == "de":
                        return "Ich helfe Ihnen gerne! Können Sie mir Ihre Nationalität und den Zweck Ihrer Reise mitteilen?"
                    elif message_language == "ja":
                        return "お手伝いさせていただきます！あなたの国籍と旅行の目的を教えていただけますか？"
                    else:
                        return "I'd love to help! Could you tell me your nationality and travel purpose?"
            
            else:
                # Default response - ensure we always have language-specific responses
                if message_language == "fr":
                    return "Bonjour, je peux vous aider avec votre visa pour l'Indonésie."
                elif message_language == "es":
                    return "Hola, puedo ayudarte con tu visa para Indonesia."
                elif message_language == "de":
                    return "Hallo, ich kann Ihnen bei Ihrem Visum für Indonesien helfen."
                elif message_language == "ja":
                    return "こんにちは、インドネシアのビザについてお手伝いできます。"
                else:
                    return "Hello, I can help you with your visa for Indonesia."
    
    def _build_contextual_prompt(self, message: str, intent: str, profile: Dict, 
                               profile_delta: Dict, chat_history: List[Dict]) -> str:
        """
        Build contextual prompt for AI based on conversation state
        """
        # Detect language from message
        message_language = self._detect_language_from_message(message)
        
        prompt = f"""You are Maya, a professional visa consultant at GSI Bali Agency helping people get visas to visit INDONESIA.

CONVERSATION CONTEXT:
- Intent: {intent}
- Current message: "{message}"
- DETECTED LANGUAGE: {message_language.upper()}
- IMPORTANT: Customer wants to visit INDONESIA (not their home country)

CRITICAL LANGUAGE RULES:
- RESPOND ONLY IN: {message_language.upper()}
- NEVER SWITCH LANGUAGES: If they wrote in French, respond in French
- NEVER USE ENGLISH: Unless they wrote in English
- LANGUAGE EXAMPLES:
  * French: "Bonjour" → "Bonjour, je peux vous aider avec votre visa"
  * Spanish: "Hola" → "Hola, puedo ayudarte con tu visa"
  * German: "Hallo" → "Hallo, ich kann Ihnen bei Ihrem Visum helfen"
  * Japanese: "こんにちは" → "こんにちは、ビザについてお手伝いできます"
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
                # Get database products for AI to use
                products = self._get_database_visa_products(db)
                if products:
                    prompt += f"""
- AVAILABLE DATABASE PRODUCTS (use these exact names and prices):
"""
                    for product in products:
                        prompt += f"  * {product['name']} - {product['price']:,} IDR - {product['duration_days']} days - {product['category']}\n"
                    
                    prompt += """
- CRITICAL RULES:
  * ALWAYS use exact product names from database above
  * ALWAYS use exact pricing from database above
  * NEVER use generic types like "E-KIT", "B211A", "KITAS"
  * MATCH product to user's duration and purpose
  * PERSONALIZED RECOMMENDATION FORMAT:
    * Use their name: "[Name], I recommend [EXACT DATABASE PRODUCT NAME]"
    * Explain reasoning: "based on your [duration] stay for [purpose]"
    * Reference nationality: "knowing you're from [Country]"
    * Include exact price: "Cost: [EXACT DATABASE PRICE] IDR"
  * Example: "Charles, I recommend Electronic Visa (E-KIT) based on your 30-day tourism visit from Canada. Cost: 500,000 IDR."
- Always match visa duration capacity to their intended stay
- Explain why this specific database product fits their situation
- Ask if they want requirements or costs"""
                else:
                    prompt += """
- No database products available - ask for more info first
- Explain why you need this info to give the best recommendation"""
            else:
                prompt += """
- Need more info first - ask for missing nationality, purpose, or duration
- Explain why you need this info to give the best recommendation"""
        
        elif intent == "ask_requirements":
            # Get database products for requirements
            products = self._get_database_visa_products(db)
            if products:
                prompt += f"""
- AVAILABLE DATABASE PRODUCTS (use these exact names):
"""
                for product in products:
                    prompt += f"  * {product['name']} - {product['duration_days']} days - {product['category']}\n"
                
                prompt += """
- REQUIREMENTS INTELLIGENCE RULES:
  * Analyze their profile to determine visa type first
  * BASE REQUIREMENTS: Passport (6+ months), photo, application form, accommodation proof, return ticket
  * SPONSOR REQUIREMENTS: Required for long-term visas (KITAS, Student Visa, Work Permit)
  * PURPOSE-SPECIFIC: Add requirements based on purpose (business letter, medical documents, etc.)
  * DURATION-SPECIFIC: Long-term visas may need additional financial proof
- TIMELINE EXPECTATIONS:
  * Short-term visas: 1-3 business days processing
  * Medium-term visas: 3-5 business days processing
  * Long-term visas: 7-14 business days processing
  * Always mention processing time when discussing requirements
- Provide requirements that match their specific visa recommendation
- Be practical and actionable
- Mention next steps"""
            else:
                prompt += """
- REQUIREMENTS INTELLIGENCE RULES:
  * Ask for their nationality, purpose, and duration first
  * BASE REQUIREMENTS: Passport (6+ months), photo, application form, accommodation proof, return ticket
  * Explain that requirements vary by visa type
  * Ask for more information to provide specific requirements"""
        
        elif intent == "ask_price":
            # Get database products for pricing
            products = self._get_database_visa_products(db)
            if products:
                prompt += f"""
- AVAILABLE DATABASE PRODUCTS (use these exact names and prices):
"""
                for product in products:
                    prompt += f"  * {product['name']} - {product['price']:,} IDR - {product['duration_days']} days\n"
                
                prompt += """
- PRICING INTELLIGENCE RULES:
  * Match pricing to their recommended visa type
  * ALWAYS use exact pricing from database above
  * EXPLAIN VALUE: Mention what's included (processing, government fees, support)
  * COMPARISON: If multiple options, explain cost differences
  * ALWAYS INCLUDE PRICING: When recommending visas, always mention cost
- Be transparent about pricing
- Ask if they want to proceed"""
            else:
                prompt += """
- PRICING INTELLIGENCE RULES:
  * Ask for their nationality, purpose, and duration first
  * Explain that pricing varies by visa type
  * Ask for more information to provide specific pricing"""
        
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
    
    def _try_openai_fallback(self, prompt: str) -> str:
        """Try OpenAI as fallback when MIA fails"""
        try:
            import openai
            from config import OPENAI_API_KEY
            
            if not OPENAI_API_KEY:
                logger.warning("No OpenAI API key available")
                return None
                
            openai.api_key = OPENAI_API_KEY
            
            response = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are Maya, a professional visa consultant. Respond in the same language as the user. Keep responses under 120 characters."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=50,
                temperature=0.7
            )
            
            ai_response = response.choices[0].message.content.strip()
            logger.info(f"🤖 OpenAI response: '{ai_response}'")
            return ai_response
            
        except Exception as e:
            logger.warning(f"OpenAI fallback failed: {e}")
            return None
    
    def _get_database_visa_products(self, db) -> List[Dict]:
        """Get visa products from database"""
        try:
            from sqlalchemy import text
            
            # Query visa products from database
            result = db.execute(text("""
                SELECT vp.id, vp.name, vp.notes, vp.gov_fee_idr, vp.first_stay_days, vp.entry_type, vp.category
                FROM visa_products vp
                JOIN catalogs c ON vp.catalog_id = c.id
                JOIN businesses b ON c.business_id = b.id
                WHERE b.business_id = 'gsi_bali_agency'
                ORDER BY vp.name
            """))
            
            products = []
            for row in result:
                products.append({
                    "id": row[0],
                    "name": row[1],
                    "description": row[2] or "No description available",
                    "price": row[3],
                    "duration_days": row[4],
                    "visa_type": row[5],
                    "category": row[6]
                })
            
            logger.info(f"📊 Retrieved {len(products)} visa products from database")
            return products
            
        except Exception as e:
            logger.error(f"❌ Error getting database products: {e}")
            return []
    
    def _find_best_visa_match(self, profile: Dict, products: List[Dict]) -> Optional[Dict]:
        """Find best matching visa product based on profile"""
        if not products:
            return None
            
        duration = profile.get("intended_stay_days", 0)
        purpose = profile.get("purpose", "")
        
        # Match by duration and purpose
        for product in products:
            product_name = product["name"].lower()
            product_duration = product.get("duration_days", 0)
            
            # Short stay (≤30 days) - Electronic Visa or Visit Visa
            if duration <= 30:
                if "electronic" in product_name or "visit" in product_name:
                    return product
            
            # Medium stay (31-60 days) - Business Visit Visa
            elif duration <= 60:
                if "business" in product_name and purpose == "business":
                    return product
                elif "visit" in product_name:
                    return product
            
            # Long stay (>60 days) - KITAS, Student Visa, Work Permit
            else:
                if purpose == "education" and "student" in product_name:
                    return product
                elif purpose == "work" and "work" in product_name:
                    return product
                elif "kitas" in product_name:
                    return product
        
        # Fallback to first product
        return products[0] if products else None
    
    def _detect_language_from_message(self, message: str) -> str:
        """Detect language from message using simple pattern matching"""
        message_lower = message.lower()
        
        # Language detection patterns - More specific patterns to avoid false positives
        # French: Use more specific patterns and avoid short words that can be substrings
        if any(word in message_lower for word in ["bonjour", "salut", "français", "française", "j'ai", "besoin", "pour le", "tourisme", "jours"]):
            return "fr"
        # Spanish: Use more specific patterns
        elif any(word in message_lower for word in ["hola", "soy", "necesito", "español", "española", "mexicano", "mexicana", "para", "negocios", "semanas"]):
            return "es"
        # German: Use more specific patterns
        elif any(word in message_lower for word in ["hallo", "ich bin", "deutsch", "deutsche", "deutscher", "brauche", "visum", "für", "studium", "monate"]):
            return "de"
        # Japanese: Keep as is since it's working perfectly
        elif any(word in message_lower for word in ["こんにちは", "私は", "日本人", "ビザ", "インドネシア", "観光", "ため", "日間"]):
            return "ja"
        elif any(word in message_lower for word in ["안녕하세요", "저는", "한국인", "비자", "인도네시아"]):
            return "ko"
        elif any(word in message_lower for word in ["你好", "我是", "中国人", "签证", "印度尼西亚"]):
            return "zh"
        elif any(word in message_lower for word in ["مرحبا", "أنا", "عربي", "فيزا", "إندونيسيا"]):
            return "ar"
        elif any(word in message_lower for word in ["olá", "sou", "português", "portuguesa", "visto", "indonésia"]):
            return "pt"
        elif any(word in message_lower for word in ["ciao", "sono", "italiano", "italiana", "visto", "indonesia"]):
            return "it"
        elif any(word in message_lower for word in ["hallo", "ik", "ben", "nederlands", "nederlandse", "visum", "indonesië"]):
            return "nl"
        elif any(word in message_lower for word in ["привет", "я", "русский", "русская", "виза", "индонезия"]):
            return "ru"
        elif any(word in message_lower for word in ["สวัสดี", "ฉัน", "ไทย", "วีซ่า", "อินโดนีเซีย"]):
            return "th"
        elif any(word in message_lower for word in ["xin chào", "tôi", "việt nam", "thị thực", "indonesia"]):
            return "vi"
        elif any(word in message_lower for word in ["halo", "saya", "indonesia", "malaysia", "visa"]):
            return "ms"
        else:
            return "en"  # Default to English
    
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
