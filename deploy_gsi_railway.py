#!/usr/bin/env python3
"""
Deploy GSI Bali Agency - Railway Console Version
Run this directly in Railway console where all dependencies are available
"""

import os
import sys
import json
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def deploy_gsi():
    """Deploy GSI Bali Agency in Railway environment"""
    logger.info("🚀 DEPLOYING GSI BALI AGENCY")
    logger.info("=" * 50)
    
    try:
        # Check environment
        visa_enabled = os.getenv("MIA_VISA_ENABLED", "false")
        logger.info(f"MIA_VISA_ENABLED: {visa_enabled}")
        
        if visa_enabled.lower() != "true":
            logger.error("❌ MIA_VISA_ENABLED must be set to 'true'")
            return False
        
        # Import required modules (available in Railway)
        try:
            from database import SessionLocal, engine
            from sqlalchemy import text
            logger.info("✅ Database modules imported")
        except ImportError as e:
            logger.error(f"❌ Import failed: {e}")
            return False
        
        # Test database connection
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return False
        
        # Run migrations
        logger.info("🔧 Running visa migrations...")
        try:
            with open('migrations/001_add_visa_tables.sql', 'r') as f:
                migration_sql = f.read()
            
            with engine.connect() as conn:
                with conn.begin():
                    statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
                    for stmt in statements:
                        if stmt:
                            conn.execute(text(stmt))
            
            logger.info("✅ Migrations completed")
        except Exception as e:
            logger.info(f"⚠️ Migration note: {e} (may already exist)")
        
        # Create GSI Agency
        logger.info("🏢 Creating GSI Bali Agency...")
        
        session = SessionLocal()
        try:
            # Check if exists
            result = session.execute(text("""
                SELECT COUNT(*) FROM businesses WHERE business_id = 'gsi_bali_agency'
            """))
            exists = result.scalar() > 0
            
            if exists:
                logger.info("✅ GSI Bali Agency already exists")
            else:
                # Create business
                business_data = {
                    'business_id': 'gsi_bali_agency',
                    'type': 'visa_agency',
                    'name': 'GSI Bali Agency',
                    'password': 'gsi2025',
                    'role': 'owner',
                    'data': json.dumps({
                        'description': 'Professional visa and KITAS services in Bali, Indonesia',
                        'location': {'address': 'Seminyak, Bali, Indonesia'},
                        'contact': {'email': 'info@gsibali.com', 'whatsapp': '+62-361-123-4567'},
                        'specialties': ['Tourist Visas', 'KITAS/ITAS', 'Visa Extensions']
                    })
                }
                
                session.execute(text("""
                    INSERT INTO businesses (business_id, type, name, password, role, data)
                    VALUES (:business_id, :type, :name, :password, :role, :data)
                """), business_data)
                
                session.commit()
                logger.info("✅ GSI business created")
            
            # Get business ID
            result = session.execute(text("""
                SELECT id FROM businesses WHERE business_id = 'gsi_bali_agency'
            """))
            business_id = result.scalar()
            
            # Create policy pack
            logger.info("📋 Creating policy pack...")
            policy_exists = session.execute(text("""
                SELECT COUNT(*) FROM policy_packs 
                WHERE business_id = :business_id AND jurisdiction = 'IDN'
            """), {'business_id': business_id}).scalar() > 0
            
            if not policy_exists:
                policy_data = {
                    "purpose_map": {"tourism": ["A1", "B1", "C1"]},
                    "hard_blocks": [{"if": "passport_validity_months < 6", "reason": "passport_validity"}],
                    "whitelists": {"A1": {"nationalities_in": ["*"]}, "B1": {"nationalities_in": ["*"]}, "C1": {"nationalities_in": ["*"]}},
                    "requirements": {
                        "A1": ["passport_validity", "return_ticket"],
                        "B1": ["passport_validity", "return_ticket", "photo_spec"],
                        "C1": ["passport_validity", "bank_statement_usd>=2000", "photo_spec"]
                    },
                    "scoring": {"base": {"A1": 0.98, "B1": 0.95, "C1": 0.90}}
                }
                
                session.execute(text("""
                    INSERT INTO policy_packs (business_id, jurisdiction, version, data_json)
                    VALUES (:business_id, 'IDN', '2025-10', :data_json)
                """), {'business_id': business_id, 'data_json': json.dumps(policy_data)})
                
                logger.info("✅ Policy pack created")
            else:
                logger.info("✅ Policy pack already exists")
            
            # Create catalog
            logger.info("📦 Creating visa catalog...")
            catalog_exists = session.execute(text("""
                SELECT COUNT(*) FROM catalogs WHERE business_id = :business_id
            """), {'business_id': business_id}).scalar() > 0
            
            if not catalog_exists:
                # Create catalog
                result = session.execute(text("""
                    INSERT INTO catalogs (business_id) VALUES (:business_id) RETURNING id
                """), {'business_id': business_id})
                catalog_id = result.scalar()
                
                # Create visa products
                products = [
                    ('A1', 'Visa Exemption (Tourism)', 30, 0, 0, 'Free visa exemption'),
                    ('B1', 'Visa on Arrival (Tourism)', 30, 500000, 1, 'Visa on arrival - extendable'),
                    ('C1', 'Tourism Visitor Visa (Single)', 60, 1000000, 5, 'Visit visa - extendable and convertible')
                ]
                
                for code, name, days, fee, sla, notes in products:
                    session.execute(text("""
                        INSERT INTO visa_products (
                            catalog_id, product_code, name, category, entry_type,
                            first_stay_days, gov_fee_idr, processing_sla_days, notes,
                            extendable_to_days, convertible, sponsor_needed
                        ) VALUES (
                            :catalog_id, :code, :name, 'tourism', 'single',
                            :days, :fee, :sla, :notes, :days, false, false
                        )
                    """), {
                        'catalog_id': catalog_id, 'code': code, 'name': name,
                        'days': days, 'fee': fee, 'sla': sla, 'notes': notes
                    })
                
                session.commit()
                logger.info(f"✅ Created catalog with {len(products)} products")
            else:
                logger.info("✅ Catalog already exists")
            
            logger.info("")
            logger.info("🎉 GSI BALI AGENCY DEPLOYMENT COMPLETE!")
            logger.info("✅ Business: gsi_bali_agency")
            logger.info("✅ Products: A1 (Free), B1 (500K IDR), C1 (1M IDR)")
            logger.info("✅ Ready to handle visa inquiries!")
            logger.info("")
            logger.info("🧪 Test with:")
            logger.info("curl -X POST /visa/chat -H 'Content-Type: application/json' \\")
            logger.info("  -d '{\"message\":\"I want to visit Bali\",\"client_id\":\"test\",\"restaurant_id\":\"gsi_bali_agency\"}'")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ GSI creation failed: {e}")
            session.rollback()
            return False
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ Deployment failed: {e}")
        return False

if __name__ == "__main__":
    success = deploy_gsi()
    if success:
        print("\n🚀 GSI BALI AGENCY IS LIVE!")
    else:
        print("\n❌ Deployment failed")
    sys.exit(0 if success else 1)
