# services/visa_chat_service_simple.py
"""
Simplified Visa Chat Service - bypasses complex flows for now
Returns proper visa responses without crashing
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from config import MIA_VISA_ENABLED
from schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)


def simple_visa_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """
    Simplified visa chat service that works without complex flows
    Returns appropriate visa responses based on message content
    """
    try:
        # Check if visa functionality is enabled
        if not MIA_VISA_ENABLED:
            return ChatResponse(
                answer="Visa services are not currently available. Please contact support.",
                response_id=None,
                confidence_score=0.0
            )
        
        # Check if this is a visa agency business
        business_type = get_business_type_simple(db, req.restaurant_id)
        if business_type != 'visa_agency':
            # Fall back to restaurant chat service
            from services.mia_chat_service_internal_tools_v5 import mia_chat_service_internal_tools_v5
            return mia_chat_service_internal_tools_v5(req, db)
        
        # Get visa products for this business
        visa_products = get_visa_products_simple(db, req.restaurant_id)
        
        # Generate appropriate response based on message content
        message_lower = req.message.lower()
        
        if any(word in message_lower for word in ['help', 'visa', 'apply', 'need']):
            if visa_products:
                product_list = []
                for product in visa_products[:3]:  # Show top 3
                    price_idr = product.get('gov_fee_idr', 0)
                    price_usd = f"${price_idr // 15000}" if price_idr > 0 else "Contact us"
                    product_list.append(f"• {product['name']} ({product['product_code']}) - {price_usd}")
                
                products_text = "\n".join(product_list)
                answer = f"I can help you with visa services! Here are some popular options:\n\n{products_text}\n\nWhich visa type interests you, or would you like more information about requirements?"
            else:
                answer = "I can help you with visa services for Indonesia. What type of visa are you looking for?"
        
        elif any(word in message_lower for word in ['tourist', 'visit', 'b211a']):
            tourist_visa = next((p for p in visa_products if 'b211a' in p['product_code'].lower()), None)
            if tourist_visa:
                price_idr = tourist_visa.get('gov_fee_idr', 0)
                price_usd = f"${price_idr // 15000}" if price_idr > 0 else "Contact us"
                answer = f"Great choice! The {tourist_visa['name']} is perfect for tourism. It allows {tourist_visa['first_stay_days']} days stay and costs {price_usd}. Would you like to know the requirements?"
            else:
                answer = "Tourist visas are available for Indonesia. Let me get you more details about the requirements and process."
        
        elif any(word in message_lower for word in ['business', 'b211b']):
            business_visa = next((p for p in visa_products if 'b211b' in p['product_code'].lower()), None)
            if business_visa:
                price_idr = business_visa.get('gov_fee_idr', 0)
                price_usd = f"${price_idr // 15000}" if price_idr > 0 else "Contact us"
                answer = f"The {business_visa['name']} is ideal for business visits. It provides {business_visa['first_stay_days']} days and costs {price_usd}. Shall I explain the application process?"
            else:
                answer = "Business visas are available for professional visits to Indonesia. Would you like more information?"
        
        elif any(word in message_lower for word in ['kitas', 'stay permit', 'b213']):
            kitas = next((p for p in visa_products if 'b213' in p['product_code'].lower() or 'kitas' in p['name'].lower()), None)
            if kitas:
                price_idr = kitas.get('gov_fee_idr', 0)
                price_usd = f"${price_idr // 15000}" if price_idr > 0 else "Contact us"
                answer = f"The {kitas['name']} is for longer stays up to {kitas['first_stay_days']} days. The government fee is {price_usd}. This requires sponsorship - would you like to discuss your eligibility?"
            else:
                answer = "KITAS (Stay Permit) is available for long-term residence in Indonesia. Let me help you understand the requirements."
        
        elif any(word in message_lower for word in ['requirements', 'documents', 'need']):
            answer = "Typical visa requirements include:\n• Valid passport (6+ months validity)\n• 2 passport photos (4x6cm, white background)\n• Financial proof (bank statement)\n• Specific documents vary by visa type\n\nWhich visa are you applying for so I can give you the exact requirements?"
        
        elif any(word in message_lower for word in ['price', 'cost', 'fee']):
            if visa_products:
                price_list = []
                for product in visa_products[:5]:
                    price_idr = product.get('gov_fee_idr', 0)
                    price_usd = f"${price_idr // 15000}" if price_idr > 0 else "Contact us"
                    price_list.append(f"• {product['name']}: {price_usd}")
                
                prices_text = "\n".join(price_list)
                answer = f"Here are our visa service fees:\n\n{prices_text}\n\nPrices include government fees and our service. Which visa interests you?"
            else:
                answer = "Visa fees vary by type. Let me know which visa you're interested in for specific pricing."
        
        else:
            # General response
            answer = "I'm here to help with your Indonesia visa needs! I can assist with:\n• Tourist visas (B211A)\n• Business visas (B211B)\n• Stay permits (KITAS)\n• Requirements and documentation\n• Application process\n\nWhat would you like to know?"
        
        # Save conversation to database
        save_chat_message_simple(db, req.client_id, req.restaurant_id, req.message, "client")
        save_chat_message_simple(db, req.client_id, req.restaurant_id, answer, "ai")
        
        return ChatResponse(
            answer=answer,
            response_id="simple_visa_service",
            confidence_score=0.9
        )
        
    except Exception as e:
        logger.error(f"Error in simple visa chat service: {str(e)}")
        return ChatResponse(
            answer="I apologize, but I'm experiencing technical difficulties. Please try again or contact our support team for assistance with your visa inquiry.",
            response_id="error",
            confidence_score=0.0
        )


def get_business_type_simple(db: Session, business_id: str) -> str:
    """Get business type using raw SQL"""
    try:
        from sqlalchemy import text
        query = text("SELECT business_type FROM businesses WHERE business_id = :business_id")
        result = db.execute(query, {"business_id": business_id}).fetchone()
        return result[0] if result else 'restaurant'
    except:
        return 'restaurant'


def get_visa_products_simple(db: Session, business_id: str) -> list:
    """Get visa products using raw SQL"""
    try:
        from sqlalchemy import text
        query = text("""
            SELECT 
                vp.product_code,
                vp.name,
                vp.category,
                vp.first_stay_days,
                vp.gov_fee_idr,
                vp.notes
            FROM visa_products vp
            JOIN catalogs c ON vp.catalog_id = c.id
            WHERE c.business_id = :business_id
            ORDER BY vp.product_code
        """)
        
        results = db.execute(query, {"business_id": business_id}).fetchall()
        
        products = []
        for row in results:
            products.append({
                "product_code": row[0],
                "name": row[1], 
                "category": row[2],
                "first_stay_days": row[3],
                "gov_fee_idr": row[4],
                "notes": row[5]
            })
        
        return products
        
    except Exception as e:
        logger.error(f"Error getting visa products: {e}")
        return []


def save_chat_message_simple(db: Session, client_id: str, restaurant_id: str, message: str, sender_type: str):
    """Save chat message using raw SQL"""
    try:
        from sqlalchemy import text
        import models
        
        # Create message using ORM (this should work)
        new_message = models.ChatMessage(
            restaurant_id=restaurant_id,
            client_id=client_id,
            sender_type=sender_type,
            message=message
        )
        db.add(new_message)
        db.commit()
        
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
