# services/visa/v1/catalog_tools.py
"""
Catalog management tools for visa agency
Handles visa product catalog and requirements retrieval
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.visa_models import Catalog, VisaProduct, VisaRequirement, VisaEligibility

logger = logging.getLogger(__name__)


def get_products(db: Session, business_id: str) -> Dict[str, Any]:
    """
    visa.v1.catalog.get_products
    
    Get all visa products for a business
    
    Args:
        business_id: Business UUID
    
    Returns:
        {
            "products": [
                {
                    "product_code": str,
                    "name": str,
                    "category": str,
                    "entry_type": str,
                    "first_stay_days": int,
                    "extendable_to_days": int,
                    "convertible": bool,
                    "sponsor_needed": bool,
                    "gov_fee_idr": int,
                    "processing_sla_days": int,
                    "notes": str
                }
            ]
        }
    """
    try:
        # Get catalog for business
        catalog = db.query(Catalog).filter(
            Catalog.business_id == business_id
        ).first()
        
        if not catalog:
            return {"products": []}
        
        # Get all products in catalog
        products = db.query(VisaProduct).filter(
            VisaProduct.catalog_id == catalog.id
        ).order_by(VisaProduct.product_code).all()
        
        product_list = []
        for product in products:
            product_list.append({
                "product_code": product.product_code,
                "name": product.name,
                "category": product.category,
                "entry_type": product.entry_type,
                "first_stay_days": product.first_stay_days,
                "extendable_to_days": product.extendable_to_days,
                "convertible": product.convertible,
                "sponsor_needed": product.sponsor_needed,
                "gov_fee_idr": product.gov_fee_idr,
                "processing_sla_days": product.processing_sla_days,
                "notes": product.notes
            })
        
        return {"products": product_list}
        
    except Exception as e:
        logger.error(f"Error getting products: {str(e)}")
        raise


def get_requirements(db: Session, business_id: str, product_code: str) -> Dict[str, Any]:
    """
    visa.v1.catalog.get_requirements
    
    Get requirements checklist for a specific visa product
    
    Args:
        business_id: Business UUID
        product_code: Visa product code (e.g., 'A1', 'B1')
    
    Returns:
        {
            "checklist": [
                {
                    "key": str,
                    "label": str,
                    "mandatory": bool,
                    "spec": str
                }
            ]
        }
    """
    try:
        # Get catalog and product
        catalog = db.query(Catalog).filter(
            Catalog.business_id == business_id
        ).first()
        
        if not catalog:
            return {"checklist": []}
        
        product = db.query(VisaProduct).filter(
            VisaProduct.catalog_id == catalog.id,
            VisaProduct.product_code == product_code
        ).first()
        
        if not product:
            return {"checklist": []}
        
        # Get requirements for product
        requirements = db.query(VisaRequirement).filter(
            VisaRequirement.visa_product_id == product.id
        ).order_by(VisaRequirement.key).all()
        
        checklist = []
        for req in requirements:
            checklist.append({
                "key": req.key,
                "label": get_requirement_label(req.key),
                "mandatory": req.mandatory,
                "spec": req.value
            })
        
        return {"checklist": checklist}
        
    except Exception as e:
        logger.error(f"Error getting requirements: {str(e)}")
        raise


def get_requirement_label(key: str) -> str:
    """
    Get human-readable label for requirement key
    """
    labels = {
        "passport_validity": "Passport Validity",
        "return_ticket": "Return Ticket",
        "bank_statement_usd": "Bank Statement (USD)",
        "photo_spec": "Passport Photo",
        "invitation_letter": "Invitation Letter",
        "health_certificate": "Health Certificate",
        "criminal_record": "Criminal Record Check",
        "travel_insurance": "Travel Insurance",
        "hotel_booking": "Hotel Booking",
        "flight_itinerary": "Flight Itinerary",
        "sponsor_letter": "Sponsor Letter",
        "company_letter": "Company Letter",
        "financial_guarantee": "Financial Guarantee"
    }
    
    return labels.get(key, key.replace("_", " ").title())


def get_product_by_code(db: Session, business_id: str, product_code: str) -> Optional[Dict[str, Any]]:
    """
    Get detailed information about a specific visa product
    
    Args:
        business_id: Business UUID
        product_code: Visa product code
    
    Returns:
        Product details or None if not found
    """
    try:
        # Get catalog and product
        catalog = db.query(Catalog).filter(
            Catalog.business_id == business_id
        ).first()
        
        if not catalog:
            return None
        
        product = db.query(VisaProduct).filter(
            VisaProduct.catalog_id == catalog.id,
            VisaProduct.product_code == product_code
        ).first()
        
        if not product:
            return None
        
        # Get requirements and eligibility
        requirements = db.query(VisaRequirement).filter(
            VisaRequirement.visa_product_id == product.id
        ).all()
        
        eligibility = db.query(VisaEligibility).filter(
            VisaEligibility.visa_product_id == product.id
        ).first()
        
        # Parse country whitelist
        eligible_countries = []
        if eligibility and eligibility.country_whitelist:
            try:
                eligible_countries = json.loads(eligibility.country_whitelist)
            except:
                eligible_countries = ["*"]  # Default to all countries
        
        return {
            "product_code": product.product_code,
            "name": product.name,
            "category": product.category,
            "entry_type": product.entry_type,
            "first_stay_days": product.first_stay_days,
            "extendable_to_days": product.extendable_to_days,
            "convertible": product.convertible,
            "sponsor_needed": product.sponsor_needed,
            "gov_fee_idr": product.gov_fee_idr,
            "processing_sla_days": product.processing_sla_days,
            "notes": product.notes,
            "requirements": [
                {
                    "key": req.key,
                    "value": req.value,
                    "mandatory": req.mandatory
                }
                for req in requirements
            ],
            "eligible_countries": eligible_countries
        }
        
    except Exception as e:
        logger.error(f"Error getting product by code: {str(e)}")
        return None
