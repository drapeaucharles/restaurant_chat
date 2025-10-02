#!/usr/bin/env python3
"""
Create GSI Bali Agency using Railway DATABASE_URL
Connects directly to production database
"""

import os
import sys
import json
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_database_url():
    """Get DATABASE_URL from environment"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL not found in environment")
        logger.info("Set DATABASE_URL environment variable with your Railway database URL")
        return None
    
    logger.info(f"✅ Using DATABASE_URL: {db_url[:50]}...")
    return db_url


def create_remote_connection(db_url):
    """Create connection to remote database"""
    try:
        # Create engine with Railway database
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            logger.info("✅ Database connection successful")
        
        return engine, SessionLocal
        
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return None, None


def run_visa_migrations(engine):
    """Run visa migrations on remote database"""
    try:
        logger.info("🔧 Running visa migrations...")
        
        # Read migration SQL
        with open('migrations/001_add_visa_tables.sql', 'r') as f:
            migration_sql = f.read()
        
        # Execute migration
        with engine.connect() as conn:
            with conn.begin():
                # Split by semicolon and execute each statement
                statements = [stmt.strip() for stmt in migration_sql.split(';') if stmt.strip()]
                
                for stmt in statements:
                    if stmt:
                        logger.debug(f"Executing: {stmt[:100]}...")
                        conn.execute(text(stmt))
        
        logger.info("✅ Visa migrations completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {e}")
        return False


def create_gsi_business(session):
    """Create GSI business record"""
    try:
        # Check if GSI already exists
        result = session.execute(text("""
            SELECT id, business_id FROM businesses 
            WHERE business_id = 'gsi_bali_agency'
        """))
        existing = result.fetchone()
        
        if existing:
            logger.info("✅ GSI Bali Agency already exists")
            return str(existing[0])
        
        # Create GSI business
        business_data = {
            'business_id': 'gsi_bali_agency',
            'type': 'visa_agency',
            'name': 'GSI Bali Agency',
            'password': 'gsi2025',
            'role': 'owner',
            'data': json.dumps({
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
                'specialties': ['Tourist Visas', 'Business Visas', 'KITAS/ITAS', 'Visa Extensions', 'Investment Visas']
            })
        }
        
        result = session.execute(text("""
            INSERT INTO businesses (business_id, type, name, password, role, data)
            VALUES (:business_id, :type, :name, :password, :role, :data)
            RETURNING id
        """), business_data)
        
        business_id = result.fetchone()[0]
        session.commit()
        
        logger.info(f"✅ Created GSI Bali Agency with ID: {business_id}")
        return str(business_id)
        
    except Exception as e:
        logger.error(f"❌ Error creating GSI business: {e}")
        session.rollback()
        raise


def create_policy_pack(session, business_id):
    """Create policy pack for GSI"""
    try:
        # Check if policy pack exists
        result = session.execute(text("""
            SELECT id FROM policy_packs 
            WHERE business_id = :business_id AND jurisdiction = 'IDN' AND version = '2025-10'
        """), {'business_id': business_id})
        existing = result.fetchone()
        
        if existing:
            logger.info("✅ Policy pack already exists")
            return str(existing[0])
        
        # Create policy pack
        policy_data = {
            "purpose_map": {
                "tourism": ["A1", "B1", "C1"],
                "business_event": ["C10", "C11"],
                "investment": ["E28A", "E28B", "E28C", "E28D", "E28F"],
                "kitas_initial": ["KITAS_B211A", "KITAS_B211B"],
                "kitas_extension": ["KITAS_EXT"]
            },
            "hard_blocks": [
                {
                    "if": "passport_validity_months < 6",
                    "reason": "passport_validity",
                    "message": "Passport must be valid for at least 6 months from entry date"
                }
            ],
            "whitelists": {
                "A1": {"nationalities_in": ["*"]},
                "B1": {"nationalities_in": ["*"]},
                "C1": {"nationalities_in": ["*"]}
            },
            "requirements": {
                "A1": ["passport_validity", "return_ticket"],
                "B1": ["passport_validity", "return_ticket", "photo_spec"],
                "C1": ["passport_validity", "bank_statement_usd>=2000", "photo_spec"]
            },
            "scoring": {
                "base": {"A1": 0.98, "B1": 0.95, "C1": 0.90},
                "bonuses": [],
                "penalties": []
            }
        }
        
        result = session.execute(text("""
            INSERT INTO policy_packs (business_id, jurisdiction, version, data_json)
            VALUES (:business_id, :jurisdiction, :version, :data_json)
            RETURNING id
        """), {
            'business_id': business_id,
            'jurisdiction': 'IDN',
            'version': '2025-10',
            'data_json': json.dumps(policy_data)
        })
        
        policy_id = result.fetchone()[0]
        session.commit()
        
        logger.info(f"✅ Created policy pack with ID: {policy_id}")
        return str(policy_id)
        
    except Exception as e:
        logger.error(f"❌ Error creating policy pack: {e}")
        session.rollback()
        raise


def create_visa_catalog(session, business_id):
    """Create visa catalog with baseline products"""
    try:
        # Check if catalog exists
        result = session.execute(text("""
            SELECT id FROM catalogs WHERE business_id = :business_id
        """), {'business_id': business_id})
        existing = result.fetchone()
        
        if existing:
            logger.info("✅ Catalog already exists")
            return str(existing[0])
        
        # Create catalog
        result = session.execute(text("""
            INSERT INTO catalogs (business_id) VALUES (:business_id) RETURNING id
        """), {'business_id': business_id})
        
        catalog_id = result.fetchone()[0]
        
        # Create baseline visa products
        products = [
            {
                'catalog_id': catalog_id,
                'product_code': 'A1',
                'name': 'Visa Exemption (Tourism)',
                'category': 'tourism',
                'entry_type': 'single',
                'first_stay_days': 30,
                'extendable_to_days': 30,
                'convertible': False,
                'sponsor_needed': False,
                'gov_fee_idr': 0,
                'processing_sla_days': 0,
                'notes': 'Free visa exemption for eligible nationalities'
            },
            {
                'catalog_id': catalog_id,
                'product_code': 'B1',
                'name': 'Visa on Arrival (Tourism)',
                'category': 'tourism',
                'entry_type': 'single',
                'first_stay_days': 30,
                'extendable_to_days': 60,
                'convertible': True,
                'sponsor_needed': False,
                'gov_fee_idr': 500000,
                'processing_sla_days': 1,
                'notes': 'Visa on arrival - extendable and convertible'
            },
            {
                'catalog_id': catalog_id,
                'product_code': 'C1',
                'name': 'Tourism Visitor Visa (Single)',
                'category': 'tourism',
                'entry_type': 'single',
                'first_stay_days': 60,
                'extendable_to_days': 180,
                'convertible': True,
                'sponsor_needed': False,
                'gov_fee_idr': 1000000,
                'processing_sla_days': 5,
                'notes': 'Single entry visit visa - extendable and convertible'
            }
        ]
        
        for product in products:
            session.execute(text("""
                INSERT INTO visa_products (
                    catalog_id, product_code, name, category, entry_type,
                    first_stay_days, extendable_to_days, convertible, sponsor_needed,
                    gov_fee_idr, processing_sla_days, notes
                ) VALUES (
                    :catalog_id, :product_code, :name, :category, :entry_type,
                    :first_stay_days, :extendable_to_days, :convertible, :sponsor_needed,
                    :gov_fee_idr, :processing_sla_days, :notes
                )
            """), product)
        
        session.commit()
        
        logger.info(f"✅ Created catalog with {len(products)} products")
        return str(catalog_id)
        
    except Exception as e:
        logger.error(f"❌ Error creating catalog: {e}")
        session.rollback()
        raise


def main():
    """Main function to create GSI using DATABASE_URL"""
    logger.info("🚀 Creating GSI Bali Agency using DATABASE_URL")
    logger.info("=" * 60)
    
    # Get database URL
    db_url = get_database_url()
    if not db_url:
        return False
    
    # Create connection
    engine, SessionLocal = create_remote_connection(db_url)
    if not engine:
        return False
    
    try:
        # Run migrations
        if not run_visa_migrations(engine):
            return False
        
        # Create GSI components
        session = SessionLocal()
        
        try:
            # Create business
            business_id = create_gsi_business(session)
            
            # Create policy pack
            policy_id = create_policy_pack(session, business_id)
            
            # Create catalog
            catalog_id = create_visa_catalog(session, business_id)
            
            logger.info("🎉 GSI BALI AGENCY CREATED SUCCESSFULLY!")
            logger.info(f"   Business ID: {business_id}")
            logger.info(f"   Policy Pack ID: {policy_id}")
            logger.info(f"   Catalog ID: {catalog_id}")
            logger.info("✅ Ready to handle visa inquiries!")
            
            return True
            
        finally:
            session.close()
            
    except Exception as e:
        logger.error(f"❌ GSI creation failed: {e}")
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
