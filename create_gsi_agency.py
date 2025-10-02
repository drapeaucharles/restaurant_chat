#!/usr/bin/env python3
"""
Create GSI Bali Agency - Specific visa agency instance
Creates the business, catalog, policy pack, and baseline products
"""

import os
import sys
import json
import logging
import uuid
from pathlib import Path

# Add parent directory to path to import database modules
sys.path.append(str(Path(__file__).parent))

from database import SessionLocal
from config import MIA_VISA_ENABLED

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_gsi_bali_agency():
    """Create GSI Bali Agency business record"""
    try:
        from models.visa_models import Business
        
        db = SessionLocal()
        
        # Check if GSI agency already exists
        existing = db.query(Business).filter(
            Business.business_id == 'gsi_bali_agency'
        ).first()
        
        if existing:
            logger.info("GSI Bali Agency already exists")
            return existing.id
        
        # Create GSI Bali Agency
        gsi_agency = Business(
            business_id='gsi_bali_agency',
            type='visa_agency',
            name='GSI Bali Agency',
            password='gsi2025',  # In production, this should be hashed
            role='owner',
            data={
                'description': 'Professional visa and KITAS services in Bali, Indonesia',
                'country_code': 'IDN',
                'location': {
                    'address': 'Jl. Raya Seminyak No. 45, Seminyak, Badung, Bali 80361, Indonesia',
                    'tz': 'Asia/Makassar'
                },
                'contact': {
                    'email': 'info@gsibali.com',
                    'whatsapp': '+62-361-123-4567',
                    'phone': '+62-361-123-4567'
                },
                'channels': {
                    'wa_number': '+62-361-123-4567',
                    'telegram': None,
                    'webchat': True
                },
                'flags': {
                    'MIA_VISA_ENABLED': True
                },
                'operating_hours': 'Mon-Fri 9:00-17:00, Sat 9:00-13:00',
                'languages': ['English', 'Indonesian', 'Mandarin', 'Russian'],
                'specialties': ['Tourist Visas', 'Business Visas', 'KITAS/ITAS', 'Visa Extensions', 'Investment Visas']
            }
        )
        
        db.add(gsi_agency)
        db.commit()
        
        logger.info(f"✅ Created GSI Bali Agency: {gsi_agency.business_id}")
        return gsi_agency.id
        
    except Exception as e:
        logger.error(f"❌ Error creating GSI Bali Agency: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_gsi_policy_pack(business_id: str):
    """Create policy pack for GSI Bali Agency (Indonesia jurisdiction)"""
    try:
        from models.visa_models import PolicyPack
        
        db = SessionLocal()
        
        # Check if policy pack already exists
        existing = db.query(PolicyPack).filter(
            PolicyPack.business_id == business_id,
            PolicyPack.jurisdiction == 'IDN',
            PolicyPack.version == '2025-10'
        ).first()
        
        if existing:
            logger.info("GSI policy pack already exists")
            return existing.id
        
        # Indonesian visa policy pack for GSI (based on immigration.pdf data)
        policy_data = {
            "purpose_map": {
                "tourism": ["A1", "B1", "C1"],
                "business_event": ["C10", "C11"],
                "investment": ["E28A", "E28B", "E28C", "E28D", "E28F"],
                "government": ["A2", "A3"],
                "crew": ["C2", "C3"],
                "transit": ["T1", "T2"],
                "diplomatic": ["D1", "D2"],
                "service": ["S1", "S2"],
                "kitas_initial": ["KITAS_B211A", "KITAS_B211B"],
                "kitas_extension": ["KITAS_EXT"]
            },
            "hard_blocks": [
                {
                    "if": "passport_validity_months < 6",
                    "reason": "passport_validity",
                    "message": "Passport must be valid for at least 6 months from entry date"
                },
                {
                    "if": "intended_stay_days > 365 and purpose != 'investment'",
                    "reason": "stay_too_long",
                    "message": "Stay duration exceeds maximum allowed for tourist visas"
                },
                {
                    "if": "nationality_iso2 in ['AF', 'IQ', 'IR']",
                    "reason": "restricted_nationality",
                    "message": "Special processing required for this nationality"
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
                "E28F": {"nationalities_in": ["*"]},
                "KITAS_B211A": {"nationalities_in": ["*"]},
                "KITAS_B211B": {"nationalities_in": ["*"]},
                "KITAS_EXT": {"nationalities_in": ["*"]}
            },
            "requirements": {
                "A1": ["passport_validity", "return_ticket"],
                "B1": ["passport_validity", "return_ticket", "photo_spec"],
                "C1": ["passport_validity", "bank_statement_usd>=2000", "photo_spec"],
                "C10": ["passport_validity", "invitation_letter", "photo_spec", "company_letter"],
                "C11": ["passport_validity", "invitation_letter", "return_ticket", "photo_spec", "company_letter"],
                "E28A": ["passport_validity", "investment_proof>=2500000", "photo_spec", "financial_guarantee"],
                "E28B": ["passport_validity", "investment_proof>=350000", "photo_spec", "sponsor_letter"],
                "E28C": ["passport_validity", "investment_proof>=200000", "photo_spec", "company_registration"],
                "E28D": ["passport_validity", "investment_proof>=130000", "photo_spec", "property_deed"],
                "E28F": ["passport_validity", "investment_proof>=70000", "photo_spec", "business_plan"],
                "KITAS_B211A": ["passport_validity", "sponsor_letter", "photo_spec", "health_certificate", "criminal_record"],
                "KITAS_B211B": ["passport_validity", "employment_contract", "photo_spec", "health_certificate", "criminal_record"],
                "KITAS_EXT": ["current_kitas", "sponsor_letter", "photo_spec", "tax_clearance"]
            },
            "scoring": {
                "base": {
                    "A1": 0.98,  # Visa exemption - highest success rate
                    "B1": 0.95,  # Visa on arrival - very high success
                    "C1": 0.90,  # Tourist visa - high success
                    "C10": 0.85, # Business event - good success
                    "C11": 0.80, # Business multiple - moderate success
                    "E28A": 0.75, # Investment high tier - moderate success
                    "E28B": 0.70, # Investment mid tier
                    "E28C": 0.68, # Investment lower tier
                    "E28D": 0.65, # Investment property
                    "E28F": 0.60, # Investment business
                    "KITAS_B211A": 0.85, # KITAS sponsor-based
                    "KITAS_B211B": 0.80, # KITAS employment-based
                    "KITAS_EXT": 0.90   # KITAS extension - high success if compliant
                },
                "bonuses": [
                    {
                        "when": "intended_stay_days <= 30",
                        "add": {"A1": 0.02, "B1": 0.03, "C1": 0.02}
                    },
                    {
                        "when": "has_return_ticket == true",
                        "add": {"A1": 0.01, "B1": 0.02, "C1": 0.03}
                    },
                    {
                        "when": "funds_usd >= 5000",
                        "add": {"C1": 0.05, "C10": 0.03, "C11": 0.03, "E28A": 0.02}
                    },
                    {
                        "when": "passport_validity_months >= 12",
                        "add": {"A1": 0.01, "B1": 0.01, "C1": 0.02, "KITAS_B211A": 0.03, "KITAS_B211B": 0.03}
                    },
                    {
                        "when": "has_previous_indonesia_visa == true",
                        "add": {"C1": 0.03, "C10": 0.05, "C11": 0.05}
                    }
                ],
                "penalties": [
                    {
                        "when": "funds_usd < 2000",
                        "sub": {"C1": 0.40, "C10": 0.25, "C11": 0.30}
                    },
                    {
                        "when": "passport_validity_months < 9",
                        "sub": {"A1": 0.05, "B1": 0.05, "C1": 0.10, "KITAS_B211A": 0.15, "KITAS_B211B": 0.15}
                    },
                    {
                        "when": "intended_stay_days > 180",
                        "sub": {"A1": 0.20, "B1": 0.15, "C1": 0.10}
                    },
                    {
                        "when": "age < 21 or age > 65",
                        "sub": {"E28A": 0.05, "E28B": 0.05, "E28C": 0.05}
                    }
                ]
            },
            "kitas_rules": {
                "initial_requirements": {
                    "min_investment_usd": 70000,
                    "sponsor_types": ["indonesian_citizen", "indonesian_company", "foreign_investment_company"],
                    "health_check_required": True,
                    "criminal_record_required": True,
                    "tax_compliance_required": False
                },
                "extension_requirements": {
                    "current_kitas_valid": True,
                    "tax_compliance_required": True,
                    "sponsor_confirmation_required": True,
                    "exit_reentry_permit": "recommended"
                },
                "conversion_paths": {
                    "C1_to_KITAS": ["sponsor_letter", "investment_proof", "health_certificate"],
                    "E28_to_KITAS": ["investment_confirmation", "tax_clearance"],
                    "B211A_to_B211B": ["employment_contract", "company_sponsorship"]
                }
            }
        }
        
        policy_pack = PolicyPack(
            business_id=business_id,
            jurisdiction='IDN',
            version='2025-10',
            data_json=policy_data
        )
        
        db.add(policy_pack)
        db.commit()
        
        logger.info(f"✅ Created GSI policy pack for IDN jurisdiction (v2025-10)")
        return policy_pack.id
        
    except Exception as e:
        logger.error(f"❌ Error creating GSI policy pack: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_gsi_catalog(business_id: str):
    """Create visa catalog with baseline products for GSI"""
    try:
        from models.visa_models import Catalog, VisaProduct, VisaRequirement, VisaEligibility
        
        db = SessionLocal()
        
        # Check if catalog already exists
        existing_catalog = db.query(Catalog).filter(
            Catalog.business_id == business_id
        ).first()
        
        if existing_catalog:
            logger.info("GSI visa catalog already exists")
            return existing_catalog.id
        
        # Create catalog
        catalog = Catalog(business_id=business_id)
        db.add(catalog)
        db.flush()  # Get catalog ID
        
        # Baseline visa products for GSI (starter set)
        visa_products = [
            {
                "product_code": "A1",
                "name": "Visa Exemption (Tourism)",
                "category": "tourism",
                "entry_type": "single",
                "first_stay_days": 30,
                "extendable_to_days": 30,
                "convertible": False,
                "sponsor_needed": False,
                "gov_fee_idr": 0,
                "processing_sla_days": 0,
                "notes": "Free visa exemption for eligible nationalities - 30 days tourism only"
            },
            {
                "product_code": "B1",
                "name": "Visa on Arrival (Tourism)",
                "category": "tourism",
                "entry_type": "single",
                "first_stay_days": 30,
                "extendable_to_days": 60,
                "convertible": True,
                "sponsor_needed": False,
                "gov_fee_idr": 500000,
                "processing_sla_days": 1,
                "notes": "Visa on arrival - can be extended once for 30 days, convertible to visit visa"
            },
            {
                "product_code": "C1",
                "name": "Tourism Visitor Visa (Single)",
                "category": "tourism",
                "entry_type": "single",
                "first_stay_days": 60,
                "extendable_to_days": 180,
                "convertible": True,
                "sponsor_needed": False,
                "gov_fee_idr": 1000000,
                "processing_sla_days": 5,
                "notes": "Single entry visit visa - extendable up to 180 days total, convertible to other visa types"
            }
        ]
        
        # Requirements mapping for baseline products
        requirements_map = {
            "A1": [
                ("passport_validity", ">=6 months", True),
                ("return_ticket", "required", True)
            ],
            "B1": [
                ("passport_validity", ">=6 months", True),
                ("return_ticket", "required", True),
                ("photo_spec", "recent color photo", True)
            ],
            "C1": [
                ("passport_validity", ">=6 months", True),
                ("bank_statement_usd", ">=2000 (last 3 months)", True),
                ("photo_spec", "recent color photo", True)
            ]
        }
        
        # Create visa products
        for product_data in visa_products:
            product = VisaProduct(
                catalog_id=catalog.id,
                **product_data
            )
            db.add(product)
            db.flush()  # Get product ID
            
            # Create requirements
            if product.product_code in requirements_map:
                for req_key, req_value, mandatory in requirements_map[product.product_code]:
                    requirement = VisaRequirement(
                        visa_product_id=product.id,
                        key=req_key,
                        value=req_value,
                        mandatory=mandatory
                    )
                    db.add(requirement)
            
            # Create eligibility (all countries eligible for baseline products)
            eligibility = VisaEligibility(
                visa_product_id=product.id,
                country_whitelist='["*"]'  # All countries eligible
            )
            db.add(eligibility)
        
        db.commit()
        
        logger.info(f"✅ Created GSI catalog with {len(visa_products)} baseline products")
        return catalog.id
        
    except Exception as e:
        logger.error(f"❌ Error creating GSI catalog: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()


def create_gsi_agency():
    """Main function to create complete GSI Bali Agency setup"""
    logger.info("🚀 Creating GSI Bali Agency...")
    
    try:
        # Create GSI Bali Agency business
        business_id = create_gsi_bali_agency()
        
        # Create policy pack for Indonesia
        policy_pack_id = create_gsi_policy_pack(business_id)
        
        # Create visa catalog with baseline products
        catalog_id = create_gsi_catalog(business_id)
        
        logger.info("✅ GSI Bali Agency creation completed successfully!")
        logger.info(f"   Business ID: {business_id}")
        logger.info(f"   Business Identifier: gsi_bali_agency")
        logger.info(f"   Policy Pack ID: {policy_pack_id}")
        logger.info(f"   Catalog ID: {catalog_id}")
        logger.info(f"   Products: A1 (Visa Exemption), B1 (Visa on Arrival), C1 (Tourist Visa)")
        
        return {
            "business_id": business_id,
            "business_identifier": "gsi_bali_agency",
            "policy_pack_id": policy_pack_id,
            "catalog_id": catalog_id,
            "status": "success"
        }
        
    except Exception as e:
        logger.error(f"❌ GSI Bali Agency creation failed: {str(e)}")
        return {
            "status": "failed",
            "error": str(e)
        }


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Create GSI Bali Agency")
    parser.add_argument("--force", action="store_true", help="Force create even if MIA_VISA_ENABLED is False")
    
    args = parser.parse_args()
    
    if args.force or MIA_VISA_ENABLED:
        if args.force and not MIA_VISA_ENABLED:
            logger.info("Force flag set - creating GSI agency regardless of MIA_VISA_ENABLED")
        
        result = create_gsi_agency()
        
        if result["status"] == "success":
            print("\n🎉 GSI BALI AGENCY READY!")
            print(f"Business ID: {result['business_identifier']}")
            print("You can now test with:")
            print(f'curl -X POST http://localhost:8000/visa/chat -H "Content-Type: application/json" -d \'{{"message": "I want to visit Bali", "client_id": "test-123", "restaurant_id": "gsi_bali_agency"}}\'')
            sys.exit(0)
        else:
            print(f"\n❌ Failed to create GSI agency: {result['error']}")
            sys.exit(1)
    else:
        logger.info("MIA_VISA_ENABLED is False - skipping GSI agency creation")
        print("Set MIA_VISA_ENABLED=true or use --force flag to create GSI agency")
        sys.exit(1)
