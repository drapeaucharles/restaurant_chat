# services/visa/v1/payment_tools.py
"""
Payment management tools for visa agency
Handles quotes, payment intents, and payment tracking
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.visa_models import VisaApplication, VisaLead, VisaProduct

logger = logging.getLogger(__name__)


def create_quote(db: Session, business_id: str, client_id: str, product_code: str, 
                add_ons: List[str] = None) -> Dict[str, Any]:
    """
    visa.v1.quote.create
    
    Create a quote for visa services
    
    Args:
        business_id: Business UUID
        client_id: Client/Lead UUID  
        product_code: Visa product code
        add_ons: List of additional services
    
    Returns:
        {
            "quote_id": str,
            "items": [
                {
                    "description": str,
                    "amount_idr": int,
                    "type": str
                }
            ],
            "total_idr": int,
            "paylink": str,
            "expires_at": str
        }
    """
    try:
        add_ons = add_ons or []
        
        # Get product details
        from .catalog_tools import get_product_by_code
        product = get_product_by_code(db, business_id, product_code)
        
        if not product:
            raise ValueError(f"Product not found: {product_code}")
        
        # Build quote items
        items = []
        total_idr = 0
        
        # Government fee
        gov_fee = product.get("gov_fee_idr", 0)
        if gov_fee > 0:
            items.append({
                "description": f"Government Fee - {product['name']}",
                "amount_idr": gov_fee,
                "type": "government_fee"
            })
            total_idr += gov_fee
        
        # Service fee (example: 15% of gov fee or minimum 500,000 IDR)
        service_fee = max(int(gov_fee * 0.15), 500000)
        items.append({
            "description": "Agency Service Fee",
            "amount_idr": service_fee,
            "type": "service_fee"
        })
        total_idr += service_fee
        
        # Add-on services
        addon_prices = get_addon_prices()
        for addon in add_ons:
            if addon in addon_prices:
                items.append({
                    "description": addon_prices[addon]["description"],
                    "amount_idr": addon_prices[addon]["price"],
                    "type": "addon"
                })
                total_idr += addon_prices[addon]["price"]
        
        # Generate quote ID and paylink
        quote_id = f"Q{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{client_id[:8]}"
        paylink = generate_paylink(quote_id, total_idr)
        
        # Quote expires in 7 days
        expires_at = (datetime.utcnow() + timedelta(days=7)).isoformat()
        
        return {
            "quote_id": quote_id,
            "items": items,
            "total_idr": total_idr,
            "paylink": paylink,
            "expires_at": expires_at
        }
        
    except Exception as e:
        logger.error(f"Error creating quote: {str(e)}")
        raise


def create_payment_intent(db: Session, app_id: str, kind: str) -> Dict[str, Any]:
    """
    visa.v1.payments.intent
    
    Create a payment intent for an application
    
    Args:
        app_id: Application UUID
        kind: Payment type ('full', 'government_fee', 'service_fee')
    
    Returns:
        {
            "payment_intent_id": str,
            "paylink": str,
            "amount_idr": int,
            "expires_at": str
        }
    """
    try:
        application = db.query(VisaApplication).filter(
            VisaApplication.id == app_id
        ).first()
        
        if not application:
            raise ValueError(f"Application not found: {app_id}")
        
        # Calculate amount based on kind
        product = application.visa_product
        amount_idr = 0
        
        if kind == 'government_fee':
            amount_idr = product.gov_fee_idr or 0
        elif kind == 'service_fee':
            # Service fee calculation
            gov_fee = product.gov_fee_idr or 0
            amount_idr = max(int(gov_fee * 0.15), 500000)
        elif kind == 'full':
            # Full payment
            gov_fee = product.gov_fee_idr or 0
            service_fee = max(int(gov_fee * 0.15), 500000)
            amount_idr = gov_fee + service_fee
        else:
            raise ValueError(f"Invalid payment kind: {kind}")
        
        # Generate payment intent
        payment_intent_id = f"PI{datetime.utcnow().strftime('%Y%m%d%H%M%S')}{app_id[:8]}"
        paylink = generate_paylink(payment_intent_id, amount_idr)
        
        # Payment expires in 24 hours
        expires_at = (datetime.utcnow() + timedelta(hours=24)).isoformat()
        
        # Update application payments
        payments = application.payments_json or []
        payments.append({
            "payment_intent_id": payment_intent_id,
            "kind": kind,
            "amount_idr": amount_idr,
            "status": "pending",
            "created_at": datetime.utcnow().isoformat(),
            "expires_at": expires_at
        })
        
        application.payments_json = payments
        db.commit()
        
        return {
            "payment_intent_id": payment_intent_id,
            "paylink": paylink,
            "amount_idr": amount_idr,
            "expires_at": expires_at
        }
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        db.rollback()
        raise


def get_addon_prices() -> Dict[str, Dict[str, Any]]:
    """
    Get pricing for add-on services
    """
    return {
        "express_processing": {
            "description": "Express Processing (3-5 days)",
            "price": 1000000  # 1M IDR
        },
        "document_review": {
            "description": "Document Review Service",
            "price": 300000   # 300K IDR
        },
        "pickup_delivery": {
            "description": "Pickup & Delivery Service",
            "price": 200000   # 200K IDR
        },
        "translation_service": {
            "description": "Document Translation",
            "price": 150000   # 150K IDR per document
        },
        "consultation": {
            "description": "1-on-1 Consultation (1 hour)",
            "price": 500000   # 500K IDR
        }
    }


def generate_paylink(payment_id: str, amount_idr: int) -> str:
    """
    Generate payment link (placeholder implementation)
    In production, this would integrate with payment gateway like Midtrans, Xendit, etc.
    """
    # This is a placeholder - in production you would:
    # 1. Create payment session with payment gateway
    # 2. Return actual payment URL
    
    base_url = "https://payment.visaagency.com"
    return f"{base_url}/pay/{payment_id}?amount={amount_idr}"


def process_payment_webhook(db: Session, payment_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Process payment webhook from payment gateway
    This would be called when payment status changes
    
    Args:
        payment_data: Payment webhook data
    
    Returns:
        {
            "status": str,
            "application_updated": bool
        }
    """
    try:
        payment_intent_id = payment_data.get("payment_intent_id")
        status = payment_data.get("status")  # "paid", "failed", "expired"
        transaction_id = payment_data.get("transaction_id")
        
        if not payment_intent_id:
            raise ValueError("Missing payment_intent_id")
        
        # Find application with this payment intent
        applications = db.query(VisaApplication).all()
        target_app = None
        
        for app in applications:
            payments = app.payments_json or []
            for payment in payments:
                if payment.get("payment_intent_id") == payment_intent_id:
                    payment["status"] = status
                    payment["transaction_id"] = transaction_id
                    payment["updated_at"] = datetime.utcnow().isoformat()
                    
                    app.payments_json = payments
                    target_app = app
                    break
            if target_app:
                break
        
        if not target_app:
            raise ValueError(f"Application not found for payment: {payment_intent_id}")
        
        # Update application status if payment successful
        if status == "paid":
            # Check if all required payments are completed
            payments = target_app.payments_json or []
            paid_payments = [p for p in payments if p.get("status") == "paid"]
            
            # If government fee is paid and docs are ready, move to submitted
            gov_fee_paid = any(p.get("kind") == "government_fee" for p in paid_payments)
            docs_ready = all(
                item.get("verified", False) 
                for item in (target_app.checklist_json or [])
                if item.get("mandatory", True)
            )
            
            if gov_fee_paid and docs_ready and target_app.status == "docs_pending":
                target_app.status = "submitted"
        
        db.commit()
        
        return {
            "status": "processed",
            "application_updated": True
        }
        
    except Exception as e:
        logger.error(f"Error processing payment webhook: {str(e)}")
        db.rollback()
        raise
