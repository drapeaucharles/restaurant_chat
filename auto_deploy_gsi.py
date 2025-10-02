#!/usr/bin/env python3
"""
Auto-deploy GSI on Railway startup
This will run automatically when the app starts
"""

import os
import sys
import json
import logging

# Simple logging
def log(message):
    print(f"[GSI-DEPLOY] {message}")

def auto_deploy_gsi():
    """Auto-deploy GSI when Railway starts"""
    try:
        # Check if visa is enabled
        if os.getenv("MIA_VISA_ENABLED", "false").lower() != "true":
            return False
        
        log("🚀 Auto-deploying GSI Bali Agency...")
        
        # Import database (available in Railway)
        from database import SessionLocal, engine
        from sqlalchemy import text
        
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        log("✅ Database connected")
        
        # First, run migrations to ensure tables exist
        log("🔧 Running visa migrations...")
        try:
            with engine.connect() as conn:
                with conn.begin():
                    # Add type column to existing restaurants table
                    conn.execute(text("""
                        ALTER TABLE restaurants 
                        ADD COLUMN IF NOT EXISTS type VARCHAR(64) DEFAULT 'restaurant'
                    """))
                    
                    # Create businesses table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS businesses (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            business_id VARCHAR UNIQUE NOT NULL,
                            type VARCHAR(64) NOT NULL DEFAULT 'restaurant',
                            name VARCHAR NOT NULL,
                            password VARCHAR NOT NULL,
                            role VARCHAR DEFAULT 'owner',
                            data JSONB DEFAULT '{}',
                            created_at TIMESTAMPTZ DEFAULT now(),
                            updated_at TIMESTAMPTZ DEFAULT now()
                        )
                    """))
                    
                    # Create policy_packs table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS policy_packs (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                            jurisdiction VARCHAR(16) NOT NULL,
                            version VARCHAR(32) NOT NULL,
                            data_json JSONB NOT NULL,
                            created_at TIMESTAMPTZ DEFAULT now(),
                            UNIQUE (business_id, jurisdiction, version)
                        )
                    """))
                    
                    # Create catalogs table
                    conn.execute(text("""
                        CREATE TABLE IF NOT EXISTS catalogs (
                            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                            business_id UUID NOT NULL REFERENCES businesses(id) ON DELETE CASCADE,
                            created_at TIMESTAMPTZ DEFAULT now()
                        )
                    """))
            
            log("✅ Migrations completed")
        except Exception as e:
            log(f"⚠️ Migration warning: {e}")
        
        session = SessionLocal()
        
        try:
            
            # Check if GSI exists
            result = session.execute(text("""
                SELECT COUNT(*) FROM businesses WHERE business_id = 'gsi_bali_agency'
            """))
            
            if result.scalar() > 0:
                log("✅ GSI Bali Agency already exists")
                return True
            
            # Create GSI
            log("🏢 Creating GSI Bali Agency...")
            session.execute(text("""
                INSERT INTO businesses (business_id, type, name, password, role, data)
                VALUES (
                    'gsi_bali_agency',
                    'visa_agency', 
                    'GSI Bali Agency',
                    'gsi2025',
                    'owner',
                    '{"description": "Professional visa services in Bali", "location": {"address": "Seminyak, Bali"}, "contact": {"email": "info@gsibali.com"}}'
                )
            """))
            
            session.commit()
            log("✅ GSI Bali Agency created successfully!")
            log("🎉 GSI is now live and ready for visa inquiries!")
            
            return True
            
        except Exception as e:
            log(f"❌ Error: {e}")
            session.rollback()
            return False
        finally:
            session.close()
            
    except ImportError:
        log("⚠️ Database modules not available (normal in local env)")
        return False
    except Exception as e:
        log(f"❌ Auto-deploy failed: {e}")
        return False

# Run auto-deploy
if __name__ == "__main__":
    auto_deploy_gsi()
