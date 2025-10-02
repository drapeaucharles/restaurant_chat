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
from services.mia_direct_api_v2 import get_mia_response_direct
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
        
        prompt = f"""You are an expert visa consultant at {business_name}, specializing in Indonesia visa services. You provide professional, accurate, and helpful visa consultation.

BUSINESS CONTEXT:
- You work for {business_name}, a professional visa agency
- You help clients obtain the right Indonesia visa for their needs
- You are knowledgeable, professional, and consultative (not pushy)

YOUR ROLE:
1. Understand client needs through natural conversation
2. Collect necessary profile information (nationality, purpose, duration)
3. Recommend appropriate visa options based on their profile
4. Explain requirements, processes, and timelines
5. Guide them through application steps when ready

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

CONVERSATION GUIDELINES:
1. Be natural, professional, and consultative
2. Ask for missing profile information when needed (nationality, purpose, duration)
3. Only recommend visas when you have sufficient profile information
4. Explain visa options clearly with benefits and requirements
5. Be helpful but not pushy - let clients decide their pace
6. Use natural language, not templates or robotic responses
7. Reference specific visa products and accurate information

IMPORTANT RULES:
- Always base recommendations on actual visa products listed above
- Don't invent visa types or requirements not in the system
- Collect profile information naturally through conversation
- Be consultative, not aggressive with recommendations
- Use professional but friendly tone

RESPONSE FORMAT:
- Respond naturally as a visa consultant would
- Ask follow-up questions when appropriate
- Provide specific visa recommendations when profile is complete
- Include next steps or call-to-action when relevant
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
        """Generate AI response using LLM"""
        
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
        
        # Build system prompt
        system_prompt = self.build_visa_system_prompt(current_profile, chat_history)
        
        # Build conversation context
        conversation_context = ""
        if chat_history:
            conversation_context = "\n\nCONVERSATION HISTORY:\n"
            for msg in chat_history[-5:]:  # Last 5 messages
                role = "Client" if msg.get("role") == "client" else "You"
                conversation_context += f"{role}: {msg.get('message', '')}\n"
        
        # Build full prompt
        full_prompt = system_prompt + conversation_context + f"\n\nClient: {message}\nVisa Consultant:"
        
        try:
            # Generate AI response
            response = get_mia_response_direct(full_prompt, {
                "temperature": 0.7,
                "max_tokens": 500,
                "top_p": 0.9
            })
            
            logger.info(f"AI generated visa response: {response[:100]}...")
            return response.strip()
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team."


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
        return ChatResponse(
            answer="I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa needs."
        )
