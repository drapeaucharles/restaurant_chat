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
        """Load policy pack (rules and requirements)"""
        try:
            query = text("""
                SELECT pp.data_json_from_pdf
                FROM policy_packs pp
                JOIN catalogs c ON pp.catalog_id = c.id
                JOIN businesses b ON c.business_id = b.id
                WHERE b.business_id = :business_id
                LIMIT 1
            """)
            
            result = self.db.execute(query, {"business_id": self.business_id}).fetchone()
            
            if result and result[0]:
                return json.loads(result[0])
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error loading policy pack: {e}")
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
                return json.loads(profile_result[0])
            else:
                return {}
                
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
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
        """Use AI to extract profile information from user message"""
        
        extraction_prompt = f"""Extract visa-related profile information from this client message.

CURRENT PROFILE: {json.dumps(current_profile)}

CLIENT MESSAGE: "{message}"

Extract any new information about:
- nationality_iso2 (2-letter country code like US, CA, AU, etc.)
- purpose (tourism, business, education, investment, family_visit, work, retirement)
- intended_stay_days (convert weeks/months/years to days)

Return ONLY a JSON object with extracted fields. If no new information, return empty object {{}}.

Examples:
"I am American" -> {{"nationality_iso2": "US"}}
"I'm from Canada for business" -> {{"nationality_iso2": "CA", "purpose": "business"}}
"Tourism for 3 weeks" -> {{"purpose": "tourism", "intended_stay_days": 21}}
"Hello" -> {{}}

JSON:"""
        
        try:
            # Use fast AI for extraction
            response = get_mia_response_fast(extraction_prompt, {
                "temperature": 0.1,
                "max_tokens": 200
            })
            
            # Parse JSON response
            response = response.strip()
            if response.startswith('```json'):
                response = response.replace('```json', '').replace('```', '').strip()
            
            extracted = json.loads(response)
            logger.info(f"AI extracted profile data: {extracted}")
            return extracted
            
        except Exception as e:
            logger.error(f"Error extracting profile with AI: {e}")
            return {}
    
    def generate_ai_response(self, message: str, client_id: str, chat_history: List[Dict]) -> str:
        """Generate conversational response (using fallback logic as primary)"""
        
        # Get current profile
        current_profile = self._get_user_profile(client_id)
        
        # Extract any new profile information from message
        profile_updates = self.extract_profile_updates(message, current_profile)
        
        # Update profile if new information found
        if profile_updates:
            updated_profile = current_profile.copy()
            updated_profile.update(profile_updates)
            self._save_user_profile(client_id, updated_profile)
            current_profile = updated_profile
        
        # Use conversational logic as primary (not fallback)
        message_lower = message.lower()
        
        # Greetings
        if any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon"]):
            return "Hi there! I'm Maya from GSI Bali Agency. I'd love to help you with your Indonesia visa! What brings you to Indonesia? 🇮🇩"
        
        # Fun/excitement responses
        elif any(word in message_lower for word in ["fun", "exciting", "adventure", "amazing"]):
            return "That's the spirit! Indonesia is absolutely amazing for fun adventures! Are you thinking beaches, culture, food, or maybe a bit of everything? And where are you traveling from?"
        
        # Finding right visa
        elif any(phrase in message_lower for phrase in ["good fit", "right visa", "best option", "find", "recommend"]):
            return "Perfect! I'd love to help you find the ideal visa for your Indonesia adventure! To recommend the best option, could you tell me: Where are you from and what's bringing you to Indonesia?"
        
        # Nationality mentions
        elif any(country in message_lower for country in ["american", "canadian", "australian", "british", "german", "french", "japanese"]):
            nationality = "American" if "american" in message_lower else "Canadian" if "canadian" in message_lower else "your"
            return f"Awesome! {nationality} travelers love Indonesia! What's bringing you there - vacation, business, or something else? And how long are you planning to stay?"
        
        # Business/tourism mentions
        elif any(word in message_lower for word in ["business", "work", "meetings", "conference"]):
            return "Business in Indonesia - how exciting! For business purposes, you'll want our Business Visit Visa (B211B). Where are you from? That helps me give you the exact requirements and processing time."
        
        elif any(word in message_lower for word in ["tourism", "vacation", "holiday", "travel", "visit"]):
            return "Indonesia for vacation - what a fantastic choice! Our Tourist Visa (B211A) is perfect for sightseeing and relaxation. Where are you traveling from and how long are you planning to stay?"
        
        # Duration mentions
        elif any(word in message_lower for word in ["weeks", "months", "days"]):
            return "Great! Knowing your travel duration helps me recommend the perfect visa. Could you also tell me where you're from and what's the main purpose of your visit?"
        
        # Visa-related questions
        elif any(word in message_lower for word in ["visa", "permit", "requirements", "documents"]):
            return "I'd be happy to help you with Indonesia visa requirements! To give you the most accurate information, could you tell me: Where are you from and what's bringing you to Indonesia?"
        
        # Default conversational response
        else:
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
