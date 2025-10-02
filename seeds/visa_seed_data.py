#!/usr/bin/env python3
"""
Visa Agency Seed Data
Creates initial data for visa products, policies, and business setup
"""

import os
import sys
import json
import logging
from pathlib import Path
import uuid

# Add parent directory to path to import database modules
sys.path.append(str(Path(__file__).parent.parent))

from database import SessionLocal
from config import MIA_VISA_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_sample_visa_agency():
    """Create a sample visa agency business"""
    try:
        from models.visa_models import Business
        
        db = SessionLocal()
        
        # Check if sample agency already exists
        existing = db.query(Business).filter(
            Business.business_id == 'jakarta_visa_agency'
        ).first()
        
        if existing:
            logger.info("Sample visa agency already exists")
            return existing.id
        
        # Create new visa agency
        agency = Business(
            business_id='jakarta_visa_agency',
            type='visa_agency',
            name='Jakarta Visa Services',
            password='demo123',  # In production, this should be hashed
            role='owner',
            data={
                'description': 'Professional visa services for Indonesia',
                'contact_email': 'info@jakartavisa.com',
                'contact_phone': '+62-21-1234-5678',
                'address': 'Jl. Sudirman No. 123, Jakarta Pusat',
                'operating_hours': 'Mon-Fri 9:00-17:00',
                'languages': ['English', 'Indonesian', 'Mandarin']
            }
        )
        
        db.add(agency)
        db.commit()
        
        logger.info(f"Created sample visa agency: {agency.business_id}")
        return agency.id
        
    except Exception as e:
        logger.error(f"Error creating sample visa agency: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_policy_pack(business_id: str):
    """Create policy pack for Indonesian visas"""
    try:
        from models.visa_models import PolicyPack
        
        db = SessionLocal()
        
        # Check if policy pack already exists
        existing = db.query(PolicyPack).filter(
            PolicyPack.business_id == business_id,
            PolicyPack.jurisdiction == 'IDN',
            PolicyPack.version == '2025-01'
        ).first()
        
        if existing:
            logger.info("Policy pack already exists")
            return existing.id
        
        # Indonesian visa policy pack
        policy_data = {
            "purpose_map": {
                "tourism": ["A1", "B1", "C1"],
                "business_event": ["C10", "C11"],
                "investment": ["E28A", "E28B", "E28C", "E28D", "E28F"],
                "government": ["A2", "A3"],
                "crew": ["C2", "C3"],
                "transit": ["T1", "T2"],
                "diplomatic": ["D1", "D2"],
                "service": ["S1", "S2"]
            },
            "hard_blocks": [
                {
                    "if": "passport_validity_months < 6",
                    "reason": "passport_validity",
                    "message": "Passport must be valid for at least 6 months from entry date"
                },
                {
                    "if": "intended_stay_days > 365",
                    "reason": "stay_too_long",
                    "message": "Stay duration exceeds maximum allowed for tourist visas"
                }
            ],
            "whitelists": {
                "A1": {"nationalities_in": ["*"]},
                "B1": {"nationalities_in": ["*"]},
                "C1": {"nationalities_in": ["*"]},
                "C10": {"nationalities_in": ["*"]},
                "C11": {"nationalities_in": ["*"]},
                "E28A": {"nationalities_in": ["*"]},
                "E28B": {"nationalities_in": ["*"]},
                "E28C": {"nationalities_in": ["*"]},
                "E28D": {"nationalities_in": ["*"]},
                "E28F": {"nationalities_in": ["*"]}
            },
            "requirements": {
                "A1": ["passport_validity", "photo_spec"],
                "B1": ["passport_validity", "return_ticket", "photo_spec"],
                "C1": ["passport_validity", "bank_statement_usd>=2000", "return_ticket", "photo_spec"],
                "C10": ["passport_validity", "invitation_letter", "photo_spec", "company_letter"],
                "C11": ["passport_validity", "invitation_letter", "return_ticket", "photo_spec", "company_letter"],
                "E28A": ["passport_validity", "investment_proof", "photo_spec", "financial_guarantee"],
                "E28B": ["passport_validity", "investment_proof", "photo_spec", "sponsor_letter"],
                "E28C": ["passport_validity", "investment_proof", "photo_spec", "company_registration"],
                "E28D": ["passport_validity", "investment_proof", "photo_spec", "property_deed"],
                "E28F": ["passport_validity", "investment_proof", "photo_spec", "business_plan"]
            },
            "scoring": {
                "base": {
                    "A1": 0.95,
                    "B1": 0.90,
                    "C1": 0.85,
                    "C10": 0.80,
                    "C11": 0.75,
                    "E28A": 0.70,
                    "E28B": 0.68,
                    "E28C": 0.65,
                    "E28D": 0.62,
                    "E28F": 0.60
                },
                "bonuses": [
                    {
                        "when": "intended_stay_days <= 30",
                        "add": {"A1": 0.03, "B1": 0.02, "C1": 0.01}
                    },
                    {
                        "when": "has_return_ticket == true",
                        "add": {"A1": 0.02, "B1": 0.03, "C1": 0.02}
                    },
                    {
                        "when": "funds_usd >= 5000",
                        "add": {"C1": 0.05, "C10": 0.03, "C11": 0.03}
                    },
                    {
                        "when": "passport_validity_months >= 12",
                        "add": {"A1": 0.01, "B1": 0.01, "C1": 0.01}
                    }
                ],
                "penalties": [
                    {
                        "when": "funds_usd < 2000",
                        "sub": {"C1": 0.40, "C10": 0.25, "C11": 0.30}
                    },
                    {
                        "when": "passport_validity_months < 9",
                        "sub": {"A1": 0.05, "B1": 0.05, "C1": 0.05}
                    },
                    {
                        "when": "intended_stay_days > 180",
                        "sub": {"A1": 0.10, "B1": 0.08, "C1": 0.05}
                    }
                ]
            }
        }
        
        policy_pack = PolicyPack(
            business_id=business_id,
            jurisdiction='IDN',
            version='2025-01',
            data_json=policy_data
        )
        
        db.add(policy_pack)
        db.commit()
        
        logger.info(f"Created policy pack for IDN jurisdiction")
        return policy_pack.id
        
    except Exception as e:
        logger.error(f"Error creating policy pack: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_visa_catalog(business_id: str):
    """Create visa catalog with products"""
    try:
        from models.visa_models import Catalog, VisaProduct, VisaRequirement, VisaEligibility
        
        db = SessionLocal()
        
        # Check if catalog already exists
        existing_catalog = db.query(Catalog).filter(
            Catalog.business_id == business_id
        ).first()
        
        if existing_catalog:
            logger.info("Visa catalog already exists")
            return existing_catalog.id
        
        # Create catalog
        catalog = Catalog(business_id=business_id)
        db.add(catalog)
        db.flush()  # Get catalog ID
        
        # Visa products data
        visa_products = [
            {
                "product_code": "A1",
                "name": "Tourist Visa (Single Entry)",
                "category": "tourism",
                "entry_type": "single",
                "first_stay_days": 30,
                "extendable_to_days": 60,
                "convertible": False,
                "sponsor_needed": False,
                "gov_fee_idr": 500000,
                "processing_sla_days": 3,
                "notes": "Standard tourist visa for leisure travel"
            },
            {
                "product_code": "B1",
                "name": "Tourist Visa (Multiple Entry)",
                "category": "tourism",
                "entry_type": "multiple",
                "first_stay_days": 30,
                "extendable_to_days": 60,
                "convertible": False,
                "sponsor_needed": False,
                "gov_fee_idr": 1000000,
                "processing_sla_days": 5,
                "notes": "Multiple entry tourist visa valid for 1 year"
            },
            {
                "product_code": "C1",
                "name": "Visit Visa (Single Entry)",
                "category": "tourism",
                "entry_type": "single",
                "first_stay_days": 60,
                "extendable_to_days": 180,
                "convertible": True,
                "sponsor_needed": False,
                "gov_fee_idr": 1500000,
                "processing_sla_days": 7,
                "notes": "Visit visa for longer stays, convertible to other types"
            },
            {
                "product_code": "C10",
                "name": "Business Event Visa",
                "category": "business_event",
                "entry_type": "single",
                "first_stay_days": 30,
                "extendable_to_days": 90,
                "convertible": False,
                "sponsor_needed": True,
                "gov_fee_idr": 2000000,
                "processing_sla_days": 10,
                "notes": "For attending business meetings, conferences, seminars"
            },
            {
                "product_code": "C11",
                "name": "Business Event Visa (Multiple Entry)",
                "category": "business_event",
                "entry_type": "multiple",
                "first_stay_days": 30,
                "extendable_to_days": 90,
                "convertible": False,
                "sponsor_needed": True,
                "gov_fee_idr": 3000000,
                "processing_sla_days": 14,
                "notes": "Multiple entry for frequent business travelers"
            },
            {
                "product_code": "E28A",
                "name": "Investment Visa (Capital Investment)",
                "category": "investment",
                "entry_type": "multiple",
                "first_stay_days": 365,
                "extendable_to_days": 1095,
                "convertible": True,
                "sponsor_needed": True,
                "gov_fee_idr": 10000000,
                "processing_sla_days": 30,
                "notes": "For investors with significant capital investment"
            },
            {
                "product_code": "E28B",
                "name": "Investment Visa (Technology Transfer)",
                "category": "investment",
                "entry_type": "multiple",
                "first_stay_days": 365,
                "extendable_to_days": 1095,
                "convertible": True,
                "sponsor_needed": True,
                "gov_fee_idr": 8000000,
                "processing_sla_days": 30,
                "notes": "For technology transfer and innovation projects"
            }
        ]
        
        # Create visa products
        for product_data in visa_products:
            product = VisaProduct(
                catalog_id=catalog.id,
                **product_data
            )
            db.add(product)
            db.flush()  # Get product ID
            
            # Create requirements
            requirements_map = {
                "A1": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True)
                ],
                "B1": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("return_ticket", "Confirmed return/onward ticket", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True)
                ],
                "C1": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("bank_statement_usd", "Bank statement showing minimum USD 2,000", True),
                    ("return_ticket", "Confirmed return/onward ticket", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True)
                ],
                "C10": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("invitation_letter", "Official invitation from Indonesian company", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True),
                    ("company_letter", "Company letter from applicant's employer", True)
                ],
                "C11": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("invitation_letter", "Official invitation from Indonesian company", True),
                    ("return_ticket", "Confirmed return/onward ticket", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True),
                    ("company_letter", "Company letter from applicant's employer", True)
                ],
                "E28A": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("investment_proof", "Investment documentation (minimum USD 2.5M)", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True),
                    ("financial_guarantee", "Financial guarantee letter from bank", True)
                ],
                "E28B": [
                    ("passport_validity", "Minimum 6 months validity", True),
                    ("investment_proof", "Technology transfer agreement", True),
                    ("photo_spec", "2 passport photos (4x6cm, white background)", True),
                    ("sponsor_letter", "Sponsor letter from Indonesian partner", True)
                ]
            }
            
            if product.product_code in requirements_map:
                for req_key, req_value, mandatory in requirements_map[product.product_code]:
                    requirement = VisaRequirement(
                        visa_product_id=product.id,
                        key=req_key,
                        value=req_value,
                        mandatory=mandatory
                    )
                    db.add(requirement)
            
            # Create eligibility (all countries eligible for these visas)
            eligibility = VisaEligibility(
                visa_product_id=product.id,
                country_whitelist='["*"]'  # All countries eligible
            )
            db.add(eligibility)
        
        db.commit()
        
        logger.info(f"Created visa catalog with {len(visa_products)} products")
        return catalog.id
        
    except Exception as e:
        logger.error(f"Error creating visa catalog: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def seed_visa_data():
    """Main function to seed all visa data"""
    if not MIA_VISA_ENABLED:
        logger.info("MIA_VISA_ENABLED is False - skipping visa seeding")
        return
    
    logger.info("Starting visa data seeding...")
    
    try:
        # Create sample visa agency
        business_id = create_sample_visa_agency()
        
        # Create policy pack
        policy_pack_id = create_policy_pack(business_id)
        
        # Create visa catalog
        catalog_id = create_visa_catalog(business_id)
        
        logger.info("✅ Visa data seeding completed successfully!")
        logger.info(f"   Business ID: {business_id}")
        logger.info(f"   Policy Pack ID: {policy_pack_id}")
        logger.info(f"   Catalog ID: {catalog_id}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Visa data seeding failed: {str(e)}")
        return False


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Seed visa agency data")
    parser.add_argument("--force", action="store_true", help="Force seed even if MIA_VISA_ENABLED is False")
    
    args = parser.parse_args()
    
    if args.force:
        logger.info("Force flag set - seeding regardless of MIA_VISA_ENABLED")
        # Temporarily override the flag
        import config
        config.MIA_VISA_ENABLED = True
    
    success = seed_visa_data()
    sys.exit(0 if success else 1)
