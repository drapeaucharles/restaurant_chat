# services/visa_flow_orchestrator_working.py
"""
Working Visa Flow Orchestrator - 7-step visa processing
Uses simplified tools that work with raw SQL
"""

import json
import logging
import requests
import os
from typing import Dict, List, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")


class WorkingVisaFlowOrchestrator:
    """
    Working implementation of visa flow orchestration
    7 flows: Router → Profiler → Normalizer → Recommender → Clarifier → Explainer → Tracker
    """
    
    def __init__(self, db: Session, business_id: str):
        self.db = db
        self.business_id = business_id
        self.visa_products = self._get_visa_products()
    
    def _get_visa_products(self) -> List[Dict]:
        """Get visa products for this business using raw SQL"""
        try:
            query = text("""
                SELECT 
                    vp.product_code,
                    vp.name,
                    vp.category,
                    vp.first_stay_days,
                    vp.extendable_to_days,
                    vp.gov_fee_idr,
                    vp.processing_sla_days,
                    vp.notes,
                    vp.sponsor_needed,
                    vp.convertible
                FROM visa_products vp
                JOIN catalogs c ON vp.catalog_id = c.id
                JOIN businesses b ON c.business_id = b.id
                WHERE b.business_id = :business_id
                ORDER BY vp.product_code
            """)
            
            logger.info(f"Getting visa products for business_id: {self.business_id}")
            
            # Use a separate transaction to avoid contaminating the main session
            try:
                results = self.db.execute(query, {"business_id": self.business_id}).fetchall()
                logger.info(f"Found {len(results)} visa products")
                
                products = []
                for row in results:
                    product = {
                        "product_code": row[0],
                        "name": row[1],
                        "category": row[2],
                        "first_stay_days": row[3],
                        "extendable_to_days": row[4],
                        "gov_fee_idr": row[5],
                        "processing_sla_days": row[6],
                        "notes": row[7],
                        "sponsor_needed": row[8],
                        "convertible": row[9]
                    }
                    products.append(product)
                    logger.info(f"Added product: {product['product_code']} - {product['name']}")
                
                logger.info(f"Returning {len(products)} products")
                return products
                
            except Exception as db_error:
                logger.error(f"Database query failed: {db_error}")
                # Rollback the transaction to clean state
                try:
                    self.db.rollback()
                    logger.info("Transaction rolled back successfully")
                except Exception as rollback_error:
                    logger.error(f"Rollback failed: {rollback_error}")
                return []
            
        except Exception as e:
            logger.error(f"Error getting visa products: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return []
    
    def process_message(self, message: str, client_id: str, chat_history: List[Dict] = None) -> Dict[str, Any]:
        """
        Process message through 7-step visa flow orchestration
        
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
            router_result = self._flow_router(message, chat_history)
            intent = router_result["intent"]
            profile_delta = router_result.get("profile_delta", {})
            
            # Step 2: Profiler - Update customer profile if needed
            if profile_delta:
                profiler_result = self._flow_profiler(client_id, profile_delta)
            else:
                profiler_result = {"profile_updated": False}
            
            # Step 3: Normalizer - Standardize and validate data
            normalizer_result = self._flow_normalizer(profile_delta)
            
            # Step 4: Route to appropriate flow based on intent
            if intent == "greeting":
                return self._flow_greeting(message, client_id, chat_history)
            elif intent == "ask_recommendation":
                return self._flow_recommender(message, client_id, chat_history)
            elif intent == "ask_requirements":
                return self._flow_clarifier(message, client_id, chat_history)
            elif intent == "ask_price":
                return self._flow_explainer(message, client_id, chat_history)
            elif intent == "ask_status":
                return self._flow_tracker(message, client_id, chat_history)
            elif intent == "provide_profile_data":
                return self._flow_profiler_response(message, client_id, profile_delta)
            else:
                # Default to recommender for general queries
                return self._flow_recommender(message, client_id, chat_history)
                
        except Exception as e:
            logger.error(f"Error in visa flow orchestrator: {e}")
            return {
                "answer": "I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team.",
                "flow_used": "error",
                "tools_executed": [],
                "next_suggested_actions": []
            }
    
    def _flow_router(self, message: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Flow 1: Router - Classify intent and extract profile data
        """
        message_lower = message.lower()
        
        # Extract profile data from message
        profile_delta = {}
        
        # Extract nationality (enhanced with more countries and patterns)
        countries = {
            "usa": "US", "america": "US", "american": "US", "united states": "US",
            "uk": "GB", "britain": "GB", "british": "GB", "england": "GB", "united kingdom": "GB",
            "australia": "AU", "australian": "AU", "aussie": "AU",
            "canada": "CA", "canadian": "CA",
            "germany": "DE", "german": "DE", "deutschland": "DE",
            "france": "FR", "french": "FR", "français": "FR",
            "japan": "JP", "japanese": "JP", "nippon": "JP",
            "singapore": "SG", "singaporean": "SG",
            "malaysia": "MY", "malaysian": "MY",
            "china": "CN", "chinese": "CN", "prc": "CN",
            "india": "IN", "indian": "IN",
            "south korea": "KR", "korea": "KR", "korean": "KR",
            "thailand": "TH", "thai": "TH",
            "philippines": "PH", "filipino": "PH", "pinoy": "PH",
            "vietnam": "VN", "vietnamese": "VN",
            "netherlands": "NL", "dutch": "NL", "holland": "NL",
            "italy": "IT", "italian": "IT",
            "spain": "ES", "spanish": "ES",
            "brazil": "BR", "brazilian": "BR",
            "russia": "RU", "russian": "RU"
        }
        
        # Check for "I'm from X" or "I am X" patterns
        nationality_patterns = [
            r"i'?m from (\w+)",
            r"i am from (\w+)", 
            r"i'?m (\w+)",
            r"i am (\w+)",
            r"my nationality is (\w+)",
            r"nationality[:\s]+(\w+)"
        ]
        
        import re
        for pattern in nationality_patterns:
            match = re.search(pattern, message_lower)
            if match:
                country_mention = match.group(1)
                if country_mention in countries:
                    profile_delta["nationality_iso2"] = countries[country_mention]
                    break
        
        # Fallback: check for direct country mentions
        if "nationality_iso2" not in profile_delta:
            for country_name, code in countries.items():
                if country_name in message_lower:
                    profile_delta["nationality_iso2"] = code
                    break
        
        # Extract purpose
        if any(word in message_lower for word in ["tourist", "tourism", "vacation", "holiday"]):
            profile_delta["purpose"] = "tourism"
        elif any(word in message_lower for word in ["business", "work", "job", "employment"]):
            profile_delta["purpose"] = "business"
        elif any(word in message_lower for word in ["study", "student", "education"]):
            profile_delta["purpose"] = "education"
        elif any(word in message_lower for word in ["retire", "retirement"]):
            profile_delta["purpose"] = "retirement"
        elif any(word in message_lower for word in ["invest", "investment"]):
            profile_delta["purpose"] = "investment"
        
        # Extract intended stay duration
        import re
        duration_patterns = [
            (r"(\d+)\s*days?", "days"),
            (r"(\d+)\s*weeks?", "weeks"),
            (r"(\d+)\s*months?", "months"),
            (r"(\d+)\s*years?", "years")
        ]
        
        for pattern, unit in duration_patterns:
            match = re.search(pattern, message_lower)
            if match:
                number = int(match.group(1))
                if unit == "days":
                    profile_delta["intended_stay_days"] = number
                elif unit == "weeks":
                    profile_delta["intended_stay_days"] = number * 7
                elif unit == "months":
                    profile_delta["intended_stay_days"] = number * 30
                elif unit == "years":
                    profile_delta["intended_stay_days"] = number * 365
                break
        
        # Classify intent
        if any(word in message_lower for word in ["recommend", "suggest", "best", "which", "what visa"]):
            intent = "ask_recommendation"
        elif any(word in message_lower for word in ["requirements", "documents", "need", "required"]):
            intent = "ask_requirements"
        elif any(word in message_lower for word in ["price", "cost", "fee", "how much"]):
            intent = "ask_price"
        elif any(word in message_lower for word in ["status", "application", "progress", "track"]):
            intent = "ask_status"
        elif profile_delta:
            intent = "provide_profile_data"
        elif any(word in message_lower for word in ["hello", "hi", "hey", "good morning", "good afternoon", "how are you"]):
            intent = "greeting"
        elif len(message.strip()) < 10 and not any(word in message_lower for word in ["visa", "permit", "kitas"]):
            # Short messages without visa keywords are likely greetings or general inquiries
            intent = "greeting"
        else:
            intent = "ask_recommendation"  # Default for visa-related queries
        
        return {
            "intent": intent,
            "profile_delta": profile_delta
        }
    
    def _flow_profiler(self, client_id: str, profile_delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flow 2: Profiler - Update customer profile
        """
        try:
            # Get business UUID
            business_uuid_query = text("SELECT id FROM businesses WHERE business_id = :business_id")
            business_result = self.db.execute(business_uuid_query, {"business_id": self.business_id}).fetchone()
            
            if not business_result:
                return {"profile_updated": False, "error": "Business not found"}
            
            business_uuid = business_result[0]
            
            # Upsert profile using raw SQL
            lead_query = text("""
                SELECT profile_json FROM visa_leads 
                WHERE business_id = :business_uuid AND id = :client_id
            """)
            lead_result = self.db.execute(lead_query, {
                "business_uuid": business_uuid,
                "client_id": client_id
            }).fetchone()
            
            if lead_result:
                # Update existing
                current_profile = json.loads(lead_result[0]) if lead_result[0] else {}
                current_profile.update(profile_delta)
                
                update_query = text("""
                    UPDATE visa_leads 
                    SET profile_json = :profile_json, updated_at = now()
                    WHERE business_id = :business_uuid AND id = :client_id
                """)
                self.db.execute(update_query, {
                    "profile_json": json.dumps(current_profile),
                    "business_uuid": business_uuid,
                    "client_id": client_id
                })
            else:
                # Create new
                insert_query = text("""
                    INSERT INTO visa_leads (id, business_id, profile_json, status, created_at, updated_at)
                    VALUES (:client_id, :business_uuid, :profile_json, 'new', now(), now())
                """)
                self.db.execute(insert_query, {
                    "client_id": client_id,
                    "business_uuid": business_uuid,
                    "profile_json": json.dumps(profile_delta)
                })
            
            self.db.commit()
            return {"profile_updated": True}
            
        except Exception as e:
            logger.error(f"Error in profiler: {e}")
            return {"profile_updated": False, "error": str(e)}
    
    def _flow_normalizer(self, profile_delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Flow 3: Normalizer - Standardize and validate data
        """
        normalized = {}
        
        # Normalize nationality
        if "nationality_iso2" in profile_delta:
            normalized["nationality_iso2"] = profile_delta["nationality_iso2"].upper()
        
        # Normalize purpose
        if "purpose" in profile_delta:
            purpose_mapping = {
                "tourism": "tourism",
                "business": "business", 
                "education": "education",
                "retirement": "retirement",
                "investment": "investment"
            }
            normalized["purpose"] = purpose_mapping.get(profile_delta["purpose"], "other")
        
        # Validate stay duration
        if "intended_stay_days" in profile_delta:
            days = profile_delta["intended_stay_days"]
            if days > 0 and days <= 3650:  # Max 10 years
                normalized["intended_stay_days"] = days
        
        return normalized
    
    def _flow_greeting(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Flow 0: Greeting - Welcome new users and introduce services
        """
        # Check if this is a returning user with profile data
        profile = self._get_user_profile(client_id)
        
        if profile and any(key in profile for key in ["nationality_iso2", "purpose", "intended_stay_days"]):
            # Returning user with profile
            welcome_parts = []
            if "nationality_iso2" in profile:
                welcome_parts.append(f"nationality: {profile['nationality_iso2']}")
            if "purpose" in profile:
                welcome_parts.append(f"purpose: {profile['purpose']}")
            
            if welcome_parts:
                profile_text = ", ".join(welcome_parts)
                answer = f"Welcome back! I see you're interested in Indonesia visas ({profile_text}). How can I help you today?\n\nI can assist with:\n• Visa recommendations\n• Requirements and documentation\n• Pricing and processing times\n• Application status\n\nWhat would you like to know?"
            else:
                answer = "Welcome back! How can I help you with your Indonesia visa needs today?"
        else:
            # New user - profile-first approach
            answer = "Hello! Welcome to GSI Bali Agency. I'm here to help you find the perfect Indonesia visa for your needs.\n\nTo provide you with the most accurate recommendations, I'd like to learn a bit about your travel plans:\n\n**1. What's your nationality?** (This determines which visas you're eligible for)\n\n**2. What's the purpose of your visit?**\n   • Tourism/vacation\n   • Business meetings\n   • Work/employment\n   • Investment\n   • Family visit\n   • Other\n\n**3. How long do you plan to stay in Indonesia?**\n\nOnce I know these details, I can recommend the best visa options with accurate pricing and requirements. What's your nationality?"
        
        return {
            "answer": answer,
            "flow_used": "greeting",
            "tools_executed": ["get_profile", "welcome_user"],
            "next_suggested_actions": ["provide_profile_info", "ask_recommendation", "ask_requirements"]
        }
    
    def _flow_recommender(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Flow 4: Recommender - Suggest best visa options
        """
        logger.info(f"Recommender flow: Found {len(self.visa_products)} visa products")
        
        if not self.visa_products:
            logger.warning("No visa products found, returning generic response")
            return {
                "answer": "I can help you with visa services for Indonesia. Let me get you more information about available options.",
                "flow_used": "recommender",
                "tools_executed": ["get_visa_products"],
                "next_suggested_actions": ["ask_requirements", "ask_price"]
            }
        
        # Get user profile to make better recommendations
        profile = self._get_user_profile(client_id)
        
        # Recommend based on message content and profile
        message_lower = message.lower()
        recommendations = []
        
        if any(word in message_lower for word in ["tourist", "vacation", "holiday"]) or profile.get("purpose") == "tourism":
            tourist_visas = [p for p in self.visa_products if "tourist" in p["category"].lower() or "b211a" in p["product_code"].lower()]
            recommendations.extend(tourist_visas[:2])
        
        if any(word in message_lower for word in ["business", "work"]) or profile.get("purpose") == "business":
            business_visas = [p for p in self.visa_products if "business" in p["category"].lower() or "b211b" in p["product_code"].lower()]
            recommendations.extend(business_visas[:2])
        
        if any(word in message_lower for word in ["long", "stay", "live", "kitas"]) or (profile.get("intended_stay_days", 0) > 60):
            long_term = [p for p in self.visa_products if p["first_stay_days"] > 90]
            recommendations.extend(long_term[:2])
        
        # If no specific recommendations, show popular options
        if not recommendations:
            recommendations = self.visa_products[:3]
        
        # Format response
        if recommendations:
            visa_list = []
            for visa in recommendations[:3]:
                price_usd = f"${visa['gov_fee_idr'] // 15000}" if visa['gov_fee_idr'] > 0 else "Contact us"
                visa_list.append(f"• {visa['name']} ({visa['product_code']}) - {price_usd} - {visa['first_stay_days']} days")
            
            visas_text = "\n".join(visa_list)
            answer = f"Based on your needs, I recommend these visa options:\n\n{visas_text}\n\nWould you like to know more about requirements or start an application?"
        else:
            answer = "I can help you find the right visa for Indonesia. What's the purpose of your visit and how long do you plan to stay?"
        
        return {
            "answer": answer,
            "flow_used": "recommender",
            "tools_executed": ["get_visa_products", "analyze_profile"],
            "next_suggested_actions": ["ask_requirements", "ask_price", "start_application"]
        }
    
    def _flow_clarifier(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Flow 5: Clarifier - Ask follow-up questions and provide requirements
        """
        message_lower = message.lower()
        
        # Find specific visa mentioned
        target_visa = None
        for visa in self.visa_products:
            if (visa["product_code"].lower() in message_lower or 
                any(word in visa["name"].lower() for word in message_lower.split())):
                target_visa = visa
                break
        
        if target_visa:
            # Provide specific requirements
            requirements = [
                "• Valid passport (minimum 6 months validity)",
                "• 2 passport photos (4x6cm, white background)",
                "• Bank statement showing sufficient funds"
            ]
            
            if target_visa["sponsor_needed"]:
                requirements.append("• Sponsor letter from Indonesian entity")
            
            if "business" in target_visa["category"].lower():
                requirements.append("• Business invitation letter")
                requirements.append("• Company registration documents")
            
            if target_visa["first_stay_days"] > 90:
                requirements.append("• Health certificate")
                requirements.append("• Police clearance certificate")
            
            requirements_text = "\n".join(requirements)
            processing_time = f"{target_visa['processing_sla_days']} days" if target_visa['processing_sla_days'] else "7-14 days"
            
            answer = f"Requirements for {target_visa['name']}:\n\n{requirements_text}\n\nProcessing time: {processing_time}\n\nWould you like help preparing your application?"
        else:
            # General requirements question
            answer = "Visa requirements vary by type. Common requirements include:\n\n• Valid passport (6+ months validity)\n• Passport photos\n• Financial proof\n• Purpose-specific documents\n\nWhich specific visa are you interested in so I can give you exact requirements?"
        
        return {
            "answer": answer,
            "flow_used": "clarifier",
            "tools_executed": ["get_requirements"],
            "next_suggested_actions": ["start_application", "ask_price"]
        }
    
    def _flow_explainer(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Flow 6: Explainer - Provide detailed explanations and quotes
        """
        message_lower = message.lower()
        
        if any(word in message_lower for word in ["price", "cost", "fee"]):
            # Show pricing
            if self.visa_products:
                price_list = []
                for visa in self.visa_products[:5]:
                    price_usd = f"${visa['gov_fee_idr'] // 15000}" if visa['gov_fee_idr'] > 0 else "Contact us"
                    price_list.append(f"• {visa['name']}: {price_usd}")
                
                prices_text = "\n".join(price_list)
                answer = f"Our visa service fees:\n\n{prices_text}\n\n*Prices include government fees and our professional service*\n\nReady to start your application?"
            else:
                answer = "I'll get you detailed pricing information. Which visa type interests you?"
        else:
            # General explanation
            answer = "I can provide detailed information about:\n\n• Visa types and eligibility\n• Requirements and documentation\n• Processing times and fees\n• Application procedures\n\nWhat would you like to know more about?"
        
        return {
            "answer": answer,
            "flow_used": "explainer", 
            "tools_executed": ["get_pricing"],
            "next_suggested_actions": ["start_application", "ask_requirements"]
        }
    
    def _flow_tracker(self, message: str, client_id: str, chat_history: List[Dict]) -> Dict[str, Any]:
        """
        Flow 7: Tracker - Track application status
        """
        # Check if user has any applications
        try:
            business_uuid_query = text("SELECT id FROM businesses WHERE business_id = :business_id")
            business_result = self.db.execute(business_uuid_query, {"business_id": self.business_id}).fetchone()
            
            if business_result:
                business_uuid = business_result[0]
                
                app_query = text("""
                    SELECT status, created_at FROM visa_applications va
                    JOIN visa_leads vl ON va.visa_lead_id = vl.id
                    WHERE vl.business_id = :business_uuid AND vl.id = :client_id
                    ORDER BY va.created_at DESC LIMIT 1
                """)
                app_result = self.db.execute(app_query, {
                    "business_uuid": business_uuid,
                    "client_id": client_id
                }).fetchone()
                
                if app_result:
                    status, created_at = app_result
                    answer = f"Your visa application status: **{status.upper()}**\n\nSubmitted: {created_at.strftime('%Y-%m-%d')}\n\nWe'll notify you of any updates. Need help with anything else?"
                else:
                    answer = "You don't have any active applications yet. Would you like to start a new visa application?"
            else:
                answer = "I can help you track your visa application. Do you have an application reference number?"
                
        except Exception as e:
            logger.error(f"Error in tracker: {e}")
            answer = "I can help you track your visa application status. Please provide your reference number or let me know if you'd like to start a new application."
        
        return {
            "answer": answer,
            "flow_used": "tracker",
            "tools_executed": ["check_application_status"],
            "next_suggested_actions": ["start_new_application", "contact_support"]
        }
    
    def _flow_profiler_response(self, message: str, client_id: str, profile_delta: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle profile data updates
        """
        # Acknowledge the information and ask for next steps
        acknowledged = []
        if "nationality_iso2" in profile_delta:
            acknowledged.append(f"nationality ({profile_delta['nationality_iso2']})")
        if "purpose" in profile_delta:
            acknowledged.append(f"purpose ({profile_delta['purpose']})")
        if "intended_stay_days" in profile_delta:
            days = profile_delta['intended_stay_days']
            acknowledged.append(f"stay duration ({days} days)")
        
        # Get current profile to see what we already have
        current_profile = self._get_user_profile(client_id) or {}
        
        # Check what information we still need
        missing_info = []
        if "nationality_iso2" not in current_profile and "nationality_iso2" not in profile_delta:
            missing_info.append("nationality")
        if "purpose" not in current_profile and "purpose" not in profile_delta:
            missing_info.append("purpose")
        if "intended_stay_days" not in current_profile and "intended_stay_days" not in profile_delta:
            missing_info.append("duration")
        
        if acknowledged:
            ack_text = ", ".join(acknowledged)
            answer = f"Perfect! I've noted your {ack_text}.\n\n"
        else:
            answer = ""
        
        # Guide user through remaining steps
        if missing_info:
            if "nationality" in missing_info:
                answer += "**What's your nationality?** This helps me determine which visas you're eligible for."
            elif "purpose" in missing_info:
                answer += "**What's the purpose of your visit to Indonesia?**\n• Tourism/vacation\n• Business meetings\n• Work/employment\n• Investment\n• Family visit\n• Study\n• Other"
            elif "duration" in missing_info:
                answer += "**How long do you plan to stay in Indonesia?** (e.g., '2 weeks', '3 months', '1 year')"
        else:
            # We have all the info - provide recommendations
            answer += "Great! I have all the information I need. Let me recommend the best visa options for you:\n\n"
            rec_result = self._flow_recommender(message, client_id, [])
            answer += rec_result["answer"].split("Based on your needs, I recommend these visa options:\n\n")[1] if "Based on your needs" in rec_result["answer"] else rec_result["answer"]
        
        return {
            "answer": answer,
            "flow_used": "profiler_response",
            "tools_executed": ["update_profile", "get_recommendations"],
            "next_suggested_actions": ["ask_requirements", "start_application"]
        }
    
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
                "client_id": client_id
            }).fetchone()
            
            if profile_result and profile_result[0]:
                return json.loads(profile_result[0])
            
            return {}
            
        except Exception as e:
            logger.error(f"Error getting user profile: {e}")
            return {}
