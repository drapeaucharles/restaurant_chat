#!/usr/bin/env python3
"""
Run comprehensive visa products seed script
"""

import os
import logging
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_url():
    """Get DATABASE_URL from environment"""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        logger.error("❌ DATABASE_URL not found in environment")
        return None
    
    logger.info(f"✅ Using DATABASE_URL: {db_url[:50]}...")
    return db_url

def run_comprehensive_visa_seed():
    """Run the comprehensive visa products seed"""
    db_url = get_database_url()
    if not db_url:
        return False
    
    try:
        engine = create_engine(db_url)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        logger.info("🚀 Starting comprehensive visa products seed...")
        
        # Read the SQL file
        with open('seed_comprehensive_visa_products.sql', 'r') as f:
            sql_content = f.read()
        
        # Split by semicolon and execute each statement
        statements = [stmt.strip() for stmt in sql_content.split(';') if stmt.strip()]
        
        for i, statement in enumerate(statements):
            if statement:
                try:
                    logger.info(f"Executing statement {i+1}/{len(statements)}")
                    session.execute(text(statement))
                    session.commit()
                except Exception as e:
                    logger.error(f"Error executing statement {i+1}: {e}")
                    session.rollback()
        
        # Verify the results
        logger.info("🔍 Verifying visa products...")
        
        # Count visa products
        result = session.execute(text("""
            SELECT COUNT(*) FROM visa_products vp
            JOIN catalogs c ON vp.catalog_id = c.id
            WHERE c.business_id = '6becb7a9-f82f-4b3a-857e-28108460ee20'
        """)).fetchone()
        
        visa_count = result[0] if result else 0
        logger.info(f"✅ Total visa products created: {visa_count}")
        
        # Show all visa products
        products = session.execute(text("""
            SELECT 
                vp.product_code,
                vp.name,
                vp.category,
                vp.first_stay_days,
                vp.gov_fee_idr
            FROM visa_products vp
            JOIN catalogs c ON vp.catalog_id = c.id
            WHERE c.business_id = '6becb7a9-f82f-4b3a-857e-28108460ee20'
            ORDER BY vp.category, vp.product_code
        """)).fetchall()
        
        logger.info("📋 Visa products created:")
        for product in products:
            logger.info(f"  - {product[0]} ({product[1]}) - {product[2]} - {product[3]} days - IDR {product[4]:,}")
        
        session.close()
        logger.info("✅ Comprehensive visa products seed completed successfully!")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error running comprehensive visa seed: {e}")
        return False

if __name__ == "__main__":
    success = run_comprehensive_visa_seed()
    if success:
        logger.info("🎉 All done!")
    else:
        logger.error("💥 Failed!")
