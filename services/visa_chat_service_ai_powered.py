"""
AI-Powered Visa Chat Service
Uses real LLM/AI instead of hardcoded templates like restaurant system
"""

import logging
import json
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

# Import AI infrastructure from restaurant system
from services.mia_direct_api import get_mia_response_direct
from services.mia_fast_polling import get_mia_response_fast

from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class VisaAIService:
    """AI-powered visa consultation service using LLM"""
    
    def __init__(self, db: Session, business_id: str):
        self.db = db
        self.business_id = business_id
        self.visa_products = self._load_visa_products()
        self.policy_pack = self._load_policy_pack()
    
    def _load_visa_products(self) -> List[Dict]:
        """Load visa products for this business"""
        try:
            query = text("""
                SELECT 
                    vp.product_code,
                    vp.name,
                    vp.category,
                    vp.entry_type,
                    vp.first_stay_days,
                    vp.extendable_to_days,
                    vp.convertible,
                    vp.sponsor_needed,
                    vp.gov_fee_idr,
                    vp.processing_sla_days,
                    vp.notes
                FROM visa_products vp
                JOIN catalogs c ON vp.catalog_id = c.id
                JOIN businesses b ON c.business_id = b.id
                WHERE b.business_id = :business_id
                ORDER BY vp.product_code
            """)
            
            results = self.db.execute(query, {"business_id": self.business_id}).fetchall()
            
            products = []
            for row in results:
                products.append({
                    "product_code": row[0],
                    "name": row[1],
                    "category": row[2],
                    "entry_type": row[3],
                    "first_stay_days": row[4],
                    "extendable_to_days": row[5],
                    "convertible": row[6],
                    "sponsor_needed": row[7],
                    "gov_fee_idr": row[8],
                    "processing_sla_days": row[9],
                    "notes": row[10]
                })
            
            return products
            
        except Exception as e:
            logger.error(f"Error loading visa products: {e}")
            return []
    
    def _load_policy_pack(self) -> Dict:
        """Load policy pack (rules and requirements) - temporarily disabled due to schema issues"""
        try:
            # TODO: Fix policy_packs schema - catalog_id column missing
            # For now, return empty policy pack to avoid transaction errors
            logger.info("Policy pack loading temporarily disabled due to schema issues")
            return {}
                
        except Exception as e:
            logger.error(f"Error loading policy pack: {e}")
            try:
                self.db.rollback()
                logger.info("Rolled back failed policy pack transaction")
            except Exception as rollback_error:
                logger.error(f"Policy pack rollback failed: {rollback_error}")
            return {}
    
    def _get_user_profile(self, client_id: str) -> Dict[str, Any]:
        """Get user profile from database"""
        try:
            business_uuid_query = text("SELECT id FROM businesses WHERE business_id = :business_id")
            business_result = self.db.execute(business_uuid_query, {"business_id": self.business_id}).fetchone()
            
            if not business_result:
                return {}
            
            business_uuid = business_result[0]
            
            profile_query = text("""
                SELECT profile_json FROM visa_leads 
                WHERE business_id = :business_uuid AND id = :client_id
            """)
            profile_result = self.db.execute(profile_query, {
                "business_uuid": business_uuid,
                "client_id": str(client_id)
            }).fetchone()
            
            if profile_result and profile_result[0]:
                profile_data = profile_result[0]
                logger.debug(f"Profile data type: {type(profile_data)}, value: {profile_data}")
                
                # Handle both string and dict cases
                if isinstance(profile_data, str):
                    return json.loads(profile_data)
                elif isinstance(profile_data, dict):
                    return profile_data
                else:
                    logger.warning(f"Unexpected profile data type: {type(profile_data)}")
                    return {}
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            try:
                self.db.rollback()
                logger.info("Rolled back failed profile transaction")
            except Exception as rollback_error:
                logger.error(f"Profile rollback failed: {rollback_error}")
            return {}
    
    def _save_user_profile(self, client_id: str, profile_data: Dict[str, Any]) -> bool:
        """Save user profile to database"""
        try:
            business_uuid_query = text("SELECT id FROM businesses WHERE business_id = :business_id")
            business_result = self.db.execute(business_uuid_query, {"business_id": self.business_id}).fetchone()
            
            if not business_result:
                return False
            
            business_uuid = business_result[0]
            client_id_str = str(client_id)
            
            # Check if profile exists
            check_query = text("""
                SELECT id FROM visa_leads 
                WHERE business_id = :business_uuid AND id = :client_id
            """)
            exists = self.db.execute(check_query, {
                "business_uuid": business_uuid,
                "client_id": client_id_str
            }).fetchone()
            
            if exists:
                # Update existing
                update_query = text("""
                    UPDATE visa_leads 
                    SET profile_json = :profile_json, updated_at = now()
                    WHERE business_id = :business_uuid AND id = :client_id
                """)
                self.db.execute(update_query, {
                    "profile_json": json.dumps(profile_data),
                    "business_uuid": business_uuid,
                    "client_id": client_id_str
                })
            else:
                # Create new
                insert_query = text("""
                    INSERT INTO visa_leads (id, business_id, profile_json, status, created_at, updated_at)
                    VALUES (:client_id, :business_uuid, :profile_json, 'new', now(), now())
                """)
                self.db.execute(insert_query, {
                    "client_id": client_id_str,
                    "business_uuid": business_uuid,
                    "profile_json": json.dumps(profile_data)
                })
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving user profile: {e}")
            self.db.rollback()
            return False
    
    def build_visa_system_prompt(self, user_profile: Dict, chat_history: List[Dict]) -> str:
        """Build intelligent system prompt for visa consultation"""
        
        # Get business info
        business_name = "GSI Bali Agency"  # Could be dynamic from business table
        
        prompt = f"""You are Maya, a friendly and experienced visa consultant at {business_name}. You're passionate about helping people navigate Indonesia's visa process with ease and confidence.

PERSONALITY & TONE:
- Warm, approachable, and genuinely helpful (like talking to a knowledgeable friend)
- Use natural, conversational language - avoid formal/robotic responses
- Show enthusiasm for Indonesia and helping people achieve their travel/business goals
- Be empathetic to visa concerns and confusion - it's normal to feel overwhelmed
- Use casual phrases like "Great!", "Perfect!", "I'd love to help", "Let me walk you through this"
- Ask follow-up questions naturally, like a real conversation

CONVERSATION STYLE:
- Start with genuine interest in their plans: "What brings you to Indonesia?"
- Share relevant insights: "Indonesia is amazing for [their purpose]!"
- Use storytelling when helpful: "I've helped many [nationality] clients with similar needs"
- Make the process feel easy: "Don't worry, we'll figure this out together"
- Celebrate progress: "Awesome! Now that I know you're [nationality]..."
- Be encouraging: "You're going to love Indonesia!" or "This visa will be perfect for your plans"

YOUR ROLE:
1. Have genuine conversations about their Indonesia plans and dreams
2. Naturally discover their nationality, purpose, and duration through chat
3. Share excitement about their journey while gathering necessary info
4. Make visa recommendations feel like friendly advice, not sales pitches
5. Guide them step-by-step with encouragement and clarity

AVAILABLE VISA PRODUCTS:
"""
        
        # Add visa products information
        for product in self.visa_products:
            prompt += f"""
• {product['name']} ({product['product_code']})
  - Category: {product['category']}
  - Duration: {product['first_stay_days']} days
  - Fee: ${product['gov_fee_idr'] // 15000} USD (approx)
  - Processing: {product['processing_sla_days']} days
  - Notes: {product.get('notes', 'Standard visa')}
"""
        
        # Add user profile context if available
        if user_profile:
            prompt += f"\n\nCURRENT CLIENT PROFILE:\n"
            if 'nationality_iso2' in user_profile:
                prompt += f"- Nationality: {user_profile['nationality_iso2']}\n"
            if 'purpose' in user_profile:
                prompt += f"- Purpose: {user_profile['purpose']}\n"
            if 'intended_stay_days' in user_profile:
                prompt += f"- Intended stay: {user_profile['intended_stay_days']} days\n"
        else:
            prompt += "\n\nCURRENT CLIENT PROFILE: New client - no information collected yet\n"
        
        # Add conversation guidelines
        prompt += """

CONVERSATION EXAMPLES & GUIDELINES:

GREETING EXAMPLES:
- "Hi there! I'm Maya from GSI Bali Agency. What brings you to Indonesia? Are you planning something exciting?"
- "Hello! I'd love to help you with your Indonesia visa. Tell me about your plans - are you thinking vacation, business, or something else?"

INFORMATION GATHERING (Natural & Conversational):
- Instead of: "What is your nationality?" 
- Say: "Where are you from? I ask because different countries have different visa options available."
- Instead of: "What is your purpose?"
- Say: "That sounds exciting! What's the main reason for your trip? Business meetings, vacation, or maybe something else?"
- Instead of: "How long will you stay?"
- Say: "How long are you thinking of staying? A quick trip or planning to really explore Indonesia?"

SHARING RECOMMENDATIONS (Enthusiastic & Helpful):
- "Based on what you've told me, I think the Tourist Visa would be perfect for your plans! Here's why..."
- "Oh, you're from [country]! I've helped lots of [nationality] travelers. For your [purpose] trip, I'd recommend..."
- "You know what? Given that you're planning [duration] for [purpose], the [visa type] is going to be your best bet."

CONVERSATION FLOW RULES:
1. Always respond like you're genuinely interested in their journey
2. Share relevant insights about Indonesia when appropriate
3. Make visa information feel like friendly advice, not a sales pitch
4. Use their name if they provide it
5. Reference previous parts of the conversation naturally
6. Ask one question at a time, don't overwhelm
7. Celebrate their progress: "Great! Now that I know..."
8. Make the process feel collaborative: "Let's figure out the best option for you"

IMPORTANT RULES:
- Base all recommendations on the actual visa products listed above
- Never invent visa types or requirements
- If you don't have enough information, ask conversationally
- Keep responses concise but warm (2-4 sentences usually)
- Always end with a natural next step or question
"""
        
        return prompt
    
    def extract_profile_updates(self, message: str, current_profile: Dict) -> Dict[str, Any]:
        """Extract profile information using reliable pattern matching"""
        
        # Use pattern matching as primary method (AI disabled due to timeouts)
        logger.info("Using enhanced pattern matching for profile extraction")
        
        message_lower = message.lower()
        extracted = {}
        
        # Enhanced nationality detection
        nationality_patterns = {
            # North America
            "american": "US", "usa": "US", "america": "US", "united states": "US", "us": "US",
            "canadian": "CA", "canada": "CA",
            # Europe  
            "british": "GB", "uk": "GB", "britain": "GB", "england": "GB", "english": "GB",
            "german": "DE", "germany": "DE", "deutsch": "DE",
            "french": "FR", "france": "FR", "français": "FR",
            "italian": "IT", "italy": "IT",
            "spanish": "ES", "spain": "ES",
            "dutch": "NL", "netherlands": "NL", "holland": "NL",
            # Asia Pacific
            "australian": "AU", "australia": "AU", "aussie": "AU",
            "japanese": "JP", "japan": "JP",
            "chinese": "CN", "china": "CN",
            "korean": "KR", "korea": "KR", "south korea": "KR",
            "singaporean": "SG", "singapore": "SG",
            "malaysian": "MY", "malaysia": "MY",
            "thai": "TH", "thailand": "TH",
            "filipino": "PH", "philippines": "PH",
            "vietnamese": "VN", "vietnam": "VN",
            "indian": "IN", "india": "IN"
        }
        
        for pattern, code in nationality_patterns.items():
            if pattern in message_lower:
                extracted["nationality_iso2"] = code
                logger.info(f"🔍 NATIONALITY DETECTED: '{pattern}' → {code}")
                break
        
        # Enhanced purpose detection using semantic categories
        tourism_indicators = [
            # Direct tourism words
            "tourism", "tourist", "vacation", "holiday", "leisure", "sightseeing",
            # Activities that indicate tourism
            "beach", "beaches", "surf", "surfing", "diving", "snorkeling", "swimming",
            "sunbathing", "coconut", "tropical", "paradise", "island", "resort",
            "relax", "relaxing", "chill", "unwind", "escape", "getaway",
            "explore", "exploring", "adventure", "discover", "experience",
            "culture", "cultural", "temples", "heritage", "traditional",
            "food", "cuisine", "culinary", "taste", "eat", "restaurant",
            "photography", "photos", "scenic", "beautiful", "nature",
            "fun", "enjoy", "enjoying", "pleasure", "entertainment"
        ]
        
        business_indicators = [
            "business", "work", "working", "job", "employment", "career",
            "meeting", "meetings", "conference", "seminar", "workshop",
            "client", "clients", "customer", "customers", "partner", "partners",
            "company", "corporate", "office", "headquarters", "branch",
            "project", "deal", "contract", "negotiation", "presentation"
        ]
        
        if any(indicator in message_lower for indicator in tourism_indicators):
            extracted["purpose"] = "tourism"
            matched_indicators = [ind for ind in tourism_indicators if ind in message_lower]
            logger.info(f"🔍 TOURISM PURPOSE DETECTED: {matched_indicators}")
        elif any(indicator in message_lower for indicator in business_indicators):
            extracted["purpose"] = "business"
            matched_indicators = [ind for ind in business_indicators if ind in message_lower]
            logger.info(f"🔍 BUSINESS PURPOSE DETECTED: {matched_indicators}")
        
        # Enhanced duration extraction with intelligent parsing
        import re
        duration_patterns = [
            (r"(\d+)\s*days?", lambda x: int(x)),
            (r"(\d+)\s*weeks?", lambda x: int(x) * 7),
            (r"(\d+)\s*months?", lambda x: int(x) * 30),
            (r"(\d+)\s*years?", lambda x: int(x) * 365),
            # Handle written numbers
            (r"one\s+week", lambda x: 7),
            (r"two\s+weeks", lambda x: 14),
            (r"three\s+weeks", lambda x: 21),
            (r"one\s+month", lambda x: 30),
            (r"two\s+months", lambda x: 60),
            (r"three\s+months", lambda x: 90),
            (r"six\s+months", lambda x: 180),
            (r"one\s+year", lambda x: 365)
        ]
        
        for pattern, converter in duration_patterns:
            match = re.search(pattern, message_lower)
            if match:
                if callable(converter):
                    if pattern.startswith(r"(\d+)"):
                        extracted["intended_stay_days"] = converter(match.group(1))
                        logger.info(f"🔍 DURATION DETECTED: '{match.group(0)}' → {extracted['intended_stay_days']} days")
                    else:
                        extracted["intended_stay_days"] = converter(None)
                        logger.info(f"🔍 DURATION DETECTED: '{match.group(0)}' → {extracted['intended_stay_days']} days")
                break
        
        logger.info(f"📝 Pattern extracted: {extracted}")
        return extracted
    
    def _build_visa_ai_prompt(self, message: str, profile: Dict, chat_history: List[Dict] = None) -> str:
        """Build comprehensive AI prompt for intelligent visa consultation"""
        
        # Enhanced system prompt with detailed context
        prompt = """You are Maya, an expert visa consultant at GSI Bali Agency with deep knowledge of Indonesia visa regulations. You provide personalized, accurate, and helpful visa guidance.

YOUR EXPERTISE:
- Indonesia visa types, requirements, and processes
- Immigration law and recent policy changes
- Practical advice for different traveler profiles
- Document preparation and application procedures
- Extension and conversion processes

CONSULTATION APPROACH:
- Listen carefully to understand the customer's unique situation
- Ask intelligent follow-up questions when needed
- Provide specific, actionable recommendations
- Explain requirements clearly and completely
- Be encouraging and supportive throughout the process
- Adapt your communication style to the customer's needs

VISA CATEGORIES & DETAILS:
1. TOURIST VISAS:
   - Visa on Arrival (VOA): 30 days, extendable once to 60 days total
   - B211A Tourist Visa: 30 days, extendable to 60 days, better for planning
   
2. BUSINESS VISAS:
   - B211B Business Visa: For meetings, conferences, negotiations
   - KITAS Investment Visa: For business owners and investors
   
3. LONG-TERM VISAS (KITAS):
   - Work Visa: For employment with Indonesian companies
   - Investment Visa: For business owners (minimum investment required)
   - Retirement Visa: For retirees 55+ with pension proof
   - Spouse Visa: For spouses of Indonesian citizens
   - Remote Worker Visa: New category for digital nomads

4. SPECIAL CONSIDERATIONS:
   - Visa runs and border runs for extensions
   - Converting from tourist to KITAS
   - Multiple entry options
   - Processing times and costs vary by nationality

RESPONSE GUIDELINES:
- Be conversational and natural, not robotic
- Reference specific details from their message
- Provide practical next steps
- Mention relevant requirements or documents
- Ask clarifying questions when information is incomplete
- Show enthusiasm for helping them achieve their Indonesia goals"""
        
        # Add comprehensive profile context
        if profile:
            prompt += "\n\nCUSTOMER PROFILE:\n"
            if profile.get("nationality_iso2"):
                nationality_map = {
                    "US": "United States", "CA": "Canada", "AU": "Australia", 
                    "GB": "United Kingdom", "DE": "Germany", "FR": "France", 
                    "JP": "Japan", "CN": "China", "KR": "South Korea",
                    "SG": "Singapore", "MY": "Malaysia", "TH": "Thailand"
                }
                nationality = nationality_map.get(profile["nationality_iso2"], profile["nationality_iso2"])
                prompt += f"- Nationality: {nationality} ({profile['nationality_iso2']})\n"
            
            if profile.get("purpose"):
                prompt += f"- Travel Purpose: {profile['purpose']}\n"
            
            if profile.get("intended_stay_days"):
                days = profile["intended_stay_days"]
                months = days // 30
                years = days // 365
                if years >= 1:
                    duration = f"{years} year{'s' if years > 1 else ''} ({days} days)"
                elif months >= 1:
                    duration = f"{months} month{'s' if months > 1 else ''} ({days} days)"
                else:
                    duration = f"{days} days"
                prompt += f"- Intended Stay: {duration}\n"
            
            # Add any other profile data
            for key, value in profile.items():
                if key not in ["nationality_iso2", "purpose", "intended_stay_days"] and value:
                    prompt += f"- {key.replace('_', ' ').title()}: {value}\n"
        
        # Add conversation context for continuity
        if chat_history and len(chat_history) > 0:
            prompt += "\nCONVERSATION HISTORY:\n"
            for msg in chat_history[-5:]:  # Last 5 messages for better context
                sender = "Customer" if msg.get("sender_type") == "user" else "Maya"
                timestamp = msg.get("timestamp", "")
                prompt += f"{sender}: {msg['message']}\n"
        
        # Current message and response instruction
        prompt += f"\nCurrent Customer Message: {message}\n\nProvide a helpful, personalized response as Maya:"
        
        return prompt
    
    def generate_ai_response(self, message: str, client_id: str, chat_history: List[Dict]) -> str:
        """Generate AI-driven visa consultation response - NO hardcoded patterns!"""
        
        # Get current profile
        current_profile = self._get_user_profile(client_id)
        
        # Extract profile updates first (this is data extraction, not response generation)
        profile_updates = self.extract_profile_updates(message, current_profile)
        logger.info(f"🔍 PROFILE DEBUG - Message: '{message}'")
        logger.info(f"🔍 PROFILE DEBUG - Current profile: {current_profile}")
        logger.info(f"🔍 PROFILE DEBUG - Extracted updates: {profile_updates}")
        
        # Update profile if new information found
        if profile_updates:
            updated_profile = current_profile.copy()
            updated_profile.update(profile_updates)
            logger.info(f"🔍 PROFILE DEBUG - Updated profile: {updated_profile}")
            
            save_success = self._save_user_profile(client_id, updated_profile)
            logger.info(f"🔍 PROFILE DEBUG - Save success: {save_success}")
            
            if save_success:
                current_profile = updated_profile
                logger.info(f"🔍 PROFILE DEBUG - Profile successfully updated in memory")
            else:
                logger.error(f"🔍 PROFILE DEBUG - Failed to save profile to database")
        else:
            logger.info(f"🔍 PROFILE DEBUG - No profile updates detected")
        
        # PURE AI-DRIVEN RESPONSE - No hardcoded patterns!
        try:
            # Build comprehensive AI prompt with all context
            visa_prompt = self._build_visa_ai_prompt(message, current_profile, chat_history)
            
            # AI parameters for intelligent responses
            ai_params = {
                "max_tokens": 200,
                "temperature": 0.8  # Higher creativity for natural conversation
            }
            
            logger.info(f"🤖 Generating AI response for: '{message[:50]}...'")
            ai_response = get_mia_response_fast(visa_prompt, ai_params)
            
            if ai_response and len(ai_response.strip()) > 10 and not ai_response.startswith("I apologize"):
                logger.info(f"✅ AI response successful: {ai_response[:100]}...")
                return ai_response.strip()
            else:
                logger.warning(f"⚠️ AI response failed or too short: '{ai_response}'")
                # Try direct API as backup
                ai_response = get_mia_response_direct(visa_prompt, ai_params)
                if ai_response and len(ai_response.strip()) > 10:
                    logger.info(f"✅ Direct AI response successful: {ai_response[:100]}...")
                    return ai_response.strip()
        except Exception as e:
            logger.error(f"❌ AI response error: {e}")
        
        # MINIMAL FALLBACK - Only for complete AI failure
        logger.warning("🔄 AI completely failed, using minimal fallback")
        return "Hi! I'm Maya from GSI Bali Agency. I'm here to help you with Indonesia visa consultation. Could you tell me about your travel plans so I can provide the best guidance?"


def ai_powered_visa_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Main AI-powered visa chat service entry point"""
    
    logger.info(f"AI VISA CHAT - Business: {req.restaurant_id}, Message: '{req.message}'")
    
    try:
        # Initialize AI service
        visa_ai = VisaAIService(db, req.restaurant_id)
        
        # Get chat history
        chat_history = []
        try:
            history_query = text("""
                SELECT sender_type, message, timestamp
                FROM chat_messages 
                WHERE client_id = :client_id AND restaurant_id = :restaurant_id
                ORDER BY timestamp DESC 
                LIMIT 10
            """)
            
            results = db.execute(history_query, {
                "client_id": str(req.client_id),
                "restaurant_id": req.restaurant_id
            }).fetchall()
            
            for row in reversed(results):
                chat_history.append({
                    "role": "client" if row[0] == "client" else "ai",
                    "message": row[1],
                    "timestamp": row[2].isoformat()
                })
        except Exception as e:
            logger.warning(f"Could not load chat history: {e}")
            try:
                db.rollback()
                logger.info("Rolled back failed chat history transaction")
            except Exception as rollback_error:
                logger.error(f"Rollback failed: {rollback_error}")
        
        # Generate AI response
        answer = visa_ai.generate_ai_response(
            message=req.message,
            client_id=req.client_id,
            chat_history=chat_history
        )
        
        # Save conversation to database
        try:
            # Save client message
            client_message = models.ChatMessage(
                restaurant_id=req.restaurant_id,
                client_id=req.client_id,
                sender_type="client",
                message=req.message
            )
            db.add(client_message)
            
            # Save AI response
            ai_message = models.ChatMessage(
                restaurant_id=req.restaurant_id,
                client_id=req.client_id,
                sender_type="ai",
                message=answer
            )
            db.add(ai_message)
            
            db.commit()
            
        except Exception as e:
            logger.error(f"Error saving chat messages: {e}")
            db.rollback()
        
        return ChatResponse(answer=answer)
        
    except Exception as e:
        logger.error(f"Error in AI visa chat service: {e}", exc_info=True)
        # Provide conversational fallback response
        message_lower = req.message.lower()
        if "hello" in message_lower or "hi" in message_lower:
            fallback_answer = "Hi there! I'm Maya from GSI Bali Agency. I'd love to help you with your Indonesia visa! What brings you to Indonesia? 🇮🇩"
        elif "fun" in message_lower:
            fallback_answer = "That's the spirit! Indonesia is absolutely amazing for fun adventures! Are you thinking beaches, culture, food, or maybe a bit of everything? And where are you traveling from?"
        elif "good fit" in message_lower or "right visa" in message_lower:
            fallback_answer = "Perfect! I'd love to help you find the ideal visa for your Indonesia adventure! To recommend the best option, could you tell me: Where are you from and what's bringing you to Indonesia?"
        else:
            fallback_answer = f"Hi! I'm Maya from GSI Bali Agency, and I'm excited to help with your Indonesia visa! I see you mentioned '{req.message}' - could you tell me a bit more about your travel plans? Where are you from and what's bringing you to Indonesia?"
        
        return ChatResponse(answer=fallback_answer)
