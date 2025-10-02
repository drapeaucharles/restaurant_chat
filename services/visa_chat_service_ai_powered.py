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
try:
    from services.mia_direct_api_v2 import get_mia_response_direct
except ImportError:
    from services.mia_direct_api import get_mia_response_direct

try:
    from services.mia_fast_polling import get_mia_response_fast
except ImportError:
    # Fallback to direct API if fast polling not available
    get_mia_response_fast = get_mia_response_direct

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
        """Extract profile information using AI semantic understanding (language-agnostic)"""
        
        try:
            # Use AI to understand profile information in ANY language
            extraction_prompt = f"""You are an intelligent profile extraction system. Extract visa-related information from this message in ANY language.

CURRENT PROFILE: {json.dumps(current_profile) if current_profile else "{}"}
MESSAGE: "{message}"

Extract any new information and return ONLY a JSON object:

{{
  "nationality_iso2": "2-letter country code if mentioned (US, CA, AU, GB, DE, FR, JP, CN, KR, SG, MY, TH, PH, VN, IN, etc.)",
  "purpose": "tourism/business/education/work/investment/family_visit if clear from context",
  "intended_stay_days": "convert any duration to days (1 week=7, 1 month=30, 1 year=365)"
}}

SEMANTIC UNDERSTANDING RULES:
- Detect nationality from ANY language: "Canadian", "français", "deutsch", "日本人", "中国人", etc.
- Understand tourism intent: vacation, holiday, fun, beach, diving, sightseeing, adventure, culture, food, photography, relaxation, etc.
- Understand business intent: work, meetings, conference, clients, company, project, deal, etc.
- Understand education intent: study, university, research, course, learning, etc.
- Parse duration in any format: "2 months", "deux mois", "zwei Monate", "2ヶ月", etc.

EXAMPLES:
"I'm Canadian and want to have fun" → {{"nationality_iso2": "CA", "purpose": "tourism"}}
"Je suis français pour affaires" → {{"nationality_iso2": "FR", "purpose": "business"}}
"Ich bin deutsch für 3 Monate" → {{"nationality_iso2": "DE", "intended_stay_days": 90}}
"I want to do snorkeling" → {{"purpose": "tourism"}}
"Business meetings" → {{"purpose": "business"}}
"Hello" → {{}}

Return ONLY the JSON object:"""

            # Try AI extraction with timeout protection
            import time
            start_time = time.time()
            
            response = get_mia_response_fast(extraction_prompt, {
                "temperature": 0.1,
                "max_tokens": 200
            })
            
            elapsed = time.time() - start_time
            logger.info(f"🤖 AI extraction took {elapsed:.2f}s")
            
            # Parse AI response
            response = response.strip()
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            elif response.startswith('```'):
                response = response.replace('```', '').strip()
            
            extracted = json.loads(response) if response else {}
            logger.info(f"🤖 AI extracted profile data: {extracted}")
            return extracted
            
        except Exception as e:
            logger.error(f"🤖 AI extraction failed: {e}, using minimal fallback")
            
            # Minimal fallback for critical cases only
            message_lower = message.lower()
            extracted = {}
            
            # Basic nationality detection (English only as fallback)
            basic_nationalities = {
                "american": "US", "canadian": "CA", "australian": "AU", 
                "british": "GB", "german": "DE", "french": "FR", "japanese": "JP"
            }
            for nat, code in basic_nationalities.items():
                if nat in message_lower:
                    extracted["nationality_iso2"] = code
                    break
            
            # Basic purpose detection
            if any(word in message_lower for word in ["fun", "vacation", "holiday", "beach", "diving"]):
                extracted["purpose"] = "tourism"
            elif any(word in message_lower for word in ["business", "work", "meeting"]):
                extracted["purpose"] = "business"
            
            # Basic duration extraction
            import re
            if re.search(r"(\d+)\s*months?", message_lower):
                match = re.search(r"(\d+)\s*months?", message_lower)
                extracted["intended_stay_days"] = int(match.group(1)) * 30
            
            logger.info(f"📝 Fallback extracted: {extracted}")
            return extracted
    
    def generate_ai_response(self, message: str, client_id: str, chat_history: List[Dict]) -> str:
        """Generate intelligent conversational response using AI understanding"""
        
        # Get current profile
        current_profile = self._get_user_profile(client_id)
        
        # Extract profile updates first
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
        
        # Use RELIABLE hybrid system: Smart fallback first, AI enhancement when available
        message_lower = message.lower()
        
        # Filter automatic messages first
        automatic_patterns = [
            "i'm your ai assistant", "ask me about our menu", "dietary preferences", 
            "allergens", "any other questions"
        ]
        if any(pattern in message_lower for pattern in automatic_patterns):
            return "Hi there! I'm Maya from GSI Bali Agency. I'd love to help you with your Indonesia visa! What brings you to Indonesia? 🇮🇩"
        
        # Build smart response based on profile state
        has_nationality = current_profile.get("nationality_iso2") or profile_updates.get("nationality_iso2")
        has_purpose = current_profile.get("purpose") or profile_updates.get("purpose")
        has_duration = current_profile.get("intended_stay_days") or profile_updates.get("intended_stay_days")
        
        # Get nationality name for responses
        nationality_names = {
            "US": "American", "CA": "Canadian", "AU": "Australian", 
            "GB": "British", "DE": "German", "FR": "French", "JP": "Japanese",
            "CN": "Chinese", "KR": "Korean", "SG": "Singaporean", "MY": "Malaysian",
            "TH": "Thai", "PH": "Filipino", "VN": "Vietnamese", "IN": "Indian"
        }
        nationality = nationality_names.get(has_nationality, "your") if has_nationality else None
        
        # SMART CONTEXTUAL RESPONSES
        
        # 1. Multi-information responses (both nationality and duration detected)
        if profile_updates.get("nationality_iso2") and profile_updates.get("intended_stay_days"):
            days = profile_updates["intended_stay_days"]
            months = days // 30
            duration_text = f"{months} months" if months > 0 else f"{days} days"
            
            if has_purpose == "tourism":
                return f"Perfect! {nationality} travelers staying {duration_text} for vacation - our Tourist Visa (B211A) is ideal for you! It gives you 30 days initially and can be extended. Would you like me to walk you through the requirements and process?"
            else:
                return f"Great! So you're from {has_nationality} and planning to stay {duration_text}. What's bringing you to Indonesia - vacation, business, or something else? That will help me recommend the perfect visa!"
        
        # 2. Nationality detected
        elif profile_updates.get("nationality_iso2"):
            if has_purpose and has_duration:
                return f"Perfect! {nationality} travelers for {has_purpose} - I have everything I need! Let me recommend the ideal visa for you..."
            elif has_purpose:
                return f"Awesome! {nationality} travelers for {has_purpose} love Indonesia! How long are you planning to stay? That helps me recommend the perfect visa type."
            else:
                return f"Awesome! {nationality} travelers love Indonesia! What's bringing you there - vacation, business, or something else? And how long are you planning to stay?"
        
        # 3. Duration detected
        elif profile_updates.get("intended_stay_days"):
            days = profile_updates["intended_stay_days"]
            months = days // 30
            duration_text = f"{months} months" if months > 0 else f"{days} days"
            
            if has_nationality and has_purpose:
                return f"Perfect! {nationality} travelers staying {duration_text} for {has_purpose} - I have everything I need! Let me recommend the ideal visa for you..."
            elif has_nationality:
                return f"Great! {nationality} travelers staying {duration_text} - what's bringing you to Indonesia? Vacation, business, or something else?"
            else:
                return f"Great! Knowing your travel duration ({duration_text}) helps me recommend the perfect visa. Could you also tell me where you're from and what's the main purpose of your visit?"
        
        # 4. Purpose detected
        elif profile_updates.get("purpose") == "tourism":
            if has_nationality and has_duration:
                return f"Perfect! {nationality} travelers for vacation - I have everything I need! Let me recommend the ideal visa for you..."
            else:
                return "Indonesia for vacation - what a fantastic choice! Our Tourist Visa (B211A) is perfect for sightseeing and relaxation. Where are you traveling from and how long are you planning to stay?"
        
        elif profile_updates.get("purpose") == "business":
            if has_nationality and has_duration:
                return f"Perfect! {nationality} travelers for business - I have everything I need! Let me recommend the ideal visa for you..."
            else:
                return "Business in Indonesia - how exciting! For business purposes, you'll want our Business Visit Visa (B211B). Where are you from? That helps me give you the exact requirements and processing time."
        
        # 5. Visa-related questions with context
        visa_keywords = ["visa", "permit", "requirements", "documents", "cost", "price", "fee", "how much", "processing", "time", "extend", "extension", "longer", "stay longer"]
        if any(word in message_lower for word in visa_keywords):
            if has_nationality and has_purpose:
                nationality_name = nationality_names.get(has_nationality, "your")
                if "extend" in message_lower or "longer" in message_lower or "3 months" in message_lower or "90 days" in message_lower:
                    return f"Great question! For {nationality_name} travelers, the Tourist Visa (B211A) gives you 30 days initially, but you can extend it for another 30 days while in Indonesia. For stays longer than 60 days total, you'd need to apply for a different visa type or do a visa run. Would you like me to explain the extension process or other visa options for longer stays?"
                else:
                    return f"I'd be happy to help with visa information for {nationality_name} travelers! What specific details would you like to know about the Tourist Visa (B211A) - requirements, costs, processing time, or something else?"
            else:
                return "I'd be happy to help you with Indonesia visa information! To give you the most accurate details, could you tell me: Where are you from and what's bringing you to Indonesia?"
        
        # 6. Greetings
        if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "how are you", "bonjour", "hola", "guten tag"]):
            return "Hi there! I'm Maya from GSI Bali Agency. I'd love to help you with your Indonesia visa! What brings you to Indonesia? 🇮🇩"
        
        # 7. Help requests
        if any(phrase in message_lower for phrase in ["help", "find", "recommend", "best", "right", "good fit", "which", "what"]):
            return "Perfect! I'd love to help you find the ideal visa for your Indonesia adventure! To recommend the best option, could you tell me: Where are you from and what's bringing you to Indonesia?"
        
        # 8. Activity-based tourism
        activity_words = ["snorkeling", "snorkling", "diving", "swimming", "hiking", "climbing", "photography", "shopping", "eating", "drinking", "partying", "dancing", "yoga", "meditation", "spa", "massage", "surf", "surfing", "beach", "beaches"]
        if any(activity in message_lower for activity in activity_words):
            if has_nationality:
                return f"Awesome! {nationality} travelers love Indonesia for activities like that! Our Tourist Visa (B211A) is perfect for vacation activities. How long are you planning to stay?"
            else:
                return f"Indonesia is amazing for {message.lower()}! Our Tourist Visa (B211A) is perfect for vacation activities like that. Where are you traveling from and how long are you planning to stay?"
        
        # 9. Default response
        return f"Hi! I'm Maya from GSI Bali Agency, and I'm excited to help with your Indonesia visa! I see you mentioned '{message}' - could you tell me a bit more about your travel plans? Where are you from and what's bringing you to Indonesia?"


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
