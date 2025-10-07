"""
Visa Service Validation Rules
Prevents hardcoded product data and enforces database usage
"""

import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)

class VisaValidationRules:
    """Enforces rules against hardcoded product data"""
    
    # List of forbidden hardcoded product types
    FORBIDDEN_HARDCODED_TYPES = [
        "E-KIT", "B211A", "B211B", "KITAS", "VITAS", 
        "tourist visa", "business visa", "student visa", "work visa"
    ]
    
    # List of forbidden hardcoded pricing
    FORBIDDEN_HARDCODED_PRICES = [
        "500,000 IDR", "1,500,000 IDR", "3,000,000 IDR",
        "500000", "1500000", "3000000"
    ]
    
    @classmethod
    def validate_recommendation(cls, response: str, db: Session, business_id: str) -> Dict[str, any]:
        """
        Validate that a recommendation uses database products, not hardcoded data
        
        Returns:
            Dict with validation results and warnings
        """
        validation_result = {
            "is_valid": True,
            "warnings": [],
            "errors": [],
            "database_products_used": [],
            "hardcoded_violations": []
        }
        
        response_lower = response.lower()
        
        # Check for forbidden hardcoded types
        for forbidden_type in cls.FORBIDDEN_HARDCODED_TYPES:
            if forbidden_type.lower() in response_lower:
                validation_result["is_valid"] = False
                validation_result["hardcoded_violations"].append(f"Hardcoded visa type: {forbidden_type}")
                validation_result["errors"].append(f"❌ FORBIDDEN: Using hardcoded visa type '{forbidden_type}' instead of database products")
        
        # Check for forbidden hardcoded prices
        for forbidden_price in cls.FORBIDDEN_HARDCODED_PRICES:
            if forbidden_price.lower() in response_lower:
                validation_result["is_valid"] = False
                validation_result["hardcoded_violations"].append(f"Hardcoded price: {forbidden_price}")
                validation_result["errors"].append(f"❌ FORBIDDEN: Using hardcoded price '{forbidden_price}' instead of database pricing")
        
        # Check if response mentions actual database products
        try:
            database_products = cls._get_database_products(db, business_id)
            mentioned_products = []
            
            for product in database_products:
                product_name_lower = product["name"].lower()
                if product_name_lower in response_lower:
                    mentioned_products.append(product["name"])
                    validation_result["database_products_used"].append(product["name"])
            
            if mentioned_products:
                validation_result["warnings"].append(f"✅ GOOD: Using database products: {', '.join(mentioned_products)}")
            else:
                validation_result["warnings"].append("⚠️ WARNING: No database products mentioned in response")
                
        except Exception as e:
            validation_result["warnings"].append(f"⚠️ Could not validate database products: {e}")
        
        return validation_result
    
    @classmethod
    def _get_database_products(cls, db: Session, business_id: str) -> List[Dict]:
        """Get visa products from database"""
        try:
            products = db.query(models.VisaProduct).join(
                models.Catalog, models.VisaProduct.catalog_id == models.Catalog.id
            ).join(
                models.Business, models.Catalog.business_id == models.Business.id
            ).filter(
                models.Business.business_id == business_id
            ).all()
            
            return [
                {
                    "id": product.id,
                    "name": product.name,
                    "price": product.gov_fee_idr,
                    "duration_days": product.first_stay_days,
                    "visa_type": product.entry_type,
                    "category": product.category
                }
                for product in products
            ]
        except Exception as e:
            logger.error(f"Error getting database products: {e}")
            return []
    
    @classmethod
    def get_database_recommendation(cls, profile: Dict, db: Session, business_id: str) -> Optional[Dict]:
        """
        Get a proper database-driven recommendation instead of hardcoded response
        
        Returns:
            Dict with actual database product recommendation
        """
        try:
            products = cls._get_database_products(db, business_id)
            if not products:
                logger.warning("No database products found for recommendations")
                return None
            
            # Find best matching product based on profile
            recommended_product = cls._find_best_match(profile, products)
            return recommended_product
            
        except Exception as e:
            logger.error(f"Error getting database recommendation: {e}")
            return None
    
    @classmethod
    def _find_best_match(cls, profile: Dict, products: List[Dict]) -> Optional[Dict]:
        """Find best matching product based on profile data"""
        if not profile.get("intended_stay_days"):
            return products[0] if products else None
        
        duration = profile["intended_stay_days"]
        purpose = profile.get("purpose", "")
        
        # Simple matching logic - can be improved
        for product in products:
            product_duration = product.get("duration_days", 0)
            product_name = product.get("name", "").lower()
            
            # Match by duration and purpose
            if duration <= 30 and "electronic" in product_name:
                return product
            elif duration <= 60 and "business" in product_name and purpose == "business":
                return product
            elif duration > 180 and "kitas" in product_name:
                return product
        
        # Fallback to first product
        return products[0] if products else None
    
    @classmethod
    def log_violation(cls, response: str, context: str = ""):
        """Log hardcoding violations for debugging"""
        logger.error(f"🚨 HARDCODING VIOLATION DETECTED: {context}")
        logger.error(f"Response: {response[:100]}...")
        logger.error("This violates the no-hardcoding rules. Use database products instead.")

# Decorator to validate responses
def validate_no_hardcoding(func):
    """Decorator to validate that responses don't use hardcoded product data"""
    def wrapper(*args, **kwargs):
        result = func(*args, **kwargs)
        
        # Extract response and database session if available
        if isinstance(result, dict) and "answer" in result:
            response = result["answer"]
            # Try to get database session from args
            db_session = None
            for arg in args:
                if hasattr(arg, 'query'):  # SQLAlchemy session
                    db_session = arg
                    break
            
            if db_session:
                validation = VisaValidationRules.validate_recommendation(
                    response, db_session, "gsi_bali_agency"
                )
                
                if not validation["is_valid"]:
                    VisaValidationRules.log_violation(response, f"Function: {func.__name__}")
                    for error in validation["errors"]:
                        logger.error(error)
        
        return result
    return wrapper
