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
                    # Skip restaurants table (it's a view) - create businesses table directly
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
                    
                    log("✅ Businesses table created")
            
            log("✅ Core migrations completed")
        except Exception as e:
            log(f"⚠️ Migration error: {e}")
            # If businesses table creation fails, use existing restaurants table
            log("📋 Falling back to restaurants table for GSI creation")
        
        session = SessionLocal()
        
        try:
            
            # Try to check if GSI exists in businesses table
            try:
                result = session.execute(text("""
                    SELECT COUNT(*) FROM businesses WHERE business_id = 'gsi_bali_agency'
                """))
                
                if result.scalar() > 0:
                    log("✅ GSI Bali Agency already exists in businesses table")
                    return True
                
                # Create GSI in businesses table
                log("🏢 Creating GSI Bali Agency in businesses table...")
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
                log("✅ GSI Bali Agency created successfully in businesses table!")
                
            except Exception as e:
                log(f"⚠️ Businesses table approach failed: {e}")
                log("📋 Trying fallback approach using restaurants table...")
                
                # Fallback: Check if GSI exists in restaurants table
                try:
                    result = session.execute(text("""
                        SELECT COUNT(*) FROM restaurants WHERE restaurant_id = 'gsi_bali_agency'
                    """))
                    
                    if result.scalar() > 0:
                        log("✅ GSI Bali Agency already exists in restaurants table")
                        return True
                    
                    # Create GSI in restaurants table as fallback
                    session.execute(text("""
                        INSERT INTO restaurants (restaurant_id, password, role, data, business_type)
                        VALUES (
                            'gsi_bali_agency',
                            'gsi2025',
                            'owner',
                            '{"name": "GSI Bali Agency", "description": "Professional visa services in Bali", "type": "visa_agency"}',
                            'visa_agency'
                        )
                    """))
                    
                    session.commit()
                    log("✅ GSI Bali Agency created successfully in restaurants table!")
                    
                except Exception as e2:
                    log(f"❌ Fallback also failed: {e2}")
                    return False
            
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
