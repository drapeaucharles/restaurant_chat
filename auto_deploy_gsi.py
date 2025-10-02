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
        migration_success = False
        try:
            with engine.connect() as conn:
                with conn.begin():
                    # Check if restaurants table exists
                    result = conn.execute(text("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_name = 'restaurants'
                    """))
                    restaurants_exists = result.fetchone() is not None
                    
                    # Check if businesses table exists and has type column
                    result = conn.execute(text("""
                        SELECT column_name FROM information_schema.columns 
                        WHERE table_name = 'businesses' AND column_name = 'type'
                    """))
                    has_type_column = result.fetchone() is not None
                    
                    # Create restaurants table if it doesn't exist (for backward compatibility)
                    if not restaurants_exists:
                        conn.execute(text("""
                            CREATE TABLE restaurants (
                                restaurant_id VARCHAR PRIMARY KEY,
                                password VARCHAR NOT NULL,
                                role VARCHAR DEFAULT 'owner',
                                data JSONB DEFAULT '{}',
                                whatsapp_number VARCHAR,
                                whatsapp_session_id VARCHAR,
                                restaurant_category VARCHAR,
                                rag_mode VARCHAR DEFAULT 'dynamic',
                                business_type VARCHAR DEFAULT 'restaurant',
                                created_at TIMESTAMPTZ DEFAULT now(),
                                updated_at TIMESTAMPTZ DEFAULT now()
                            )
                        """))
                        log("✅ Restaurants table created for backward compatibility")
                    
                    # Create or update businesses table
                    if not has_type_column:
                        # Create businesses table without dropping restaurants
                        conn.execute(text("DROP TABLE IF EXISTS businesses CASCADE"))
                        conn.execute(text("""
                            CREATE TABLE businesses (
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
                        log("✅ Businesses table created with type column")
                    else:
                        log("✅ Businesses table already has type column")
                    
                    migration_success = True
            
            log("✅ Core migrations completed")
        except Exception as e:
            log(f"⚠️ Migration error: {e}")
            migration_success = False
        
        # Try businesses table first if migration was successful
        if migration_success:
            try:
                session = SessionLocal()
                
                # Check if GSI exists in businesses table
                result = session.execute(text("""
                    SELECT COUNT(*) FROM businesses WHERE business_id = 'gsi_bali_agency'
                """))
                
                if result.scalar() > 0:
                    log("✅ GSI Bali Agency already exists in businesses table")
                    session.close()
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
                
                # Also ensure admin users exist in restaurants table for backward compatibility
                try:
                    # Check if admin users exist in restaurants table
                    admin_exists = session.execute(text("""
                        SELECT COUNT(*) FROM restaurants WHERE restaurant_id = 'admin'
                    """)).scalar() > 0
                    
                    if not admin_exists:
                        # Create admin users
                        session.execute(text("""
                            INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode)
                            VALUES 
                            ('admin', 'admin123', 'admin', '{"name": "Admin User"}', 'admin', 'dynamic'),
                            ('admin@admin.com', 'admin123', 'admin', '{"name": "Admin Email"}', 'admin', 'dynamic')
                        """))
                        session.commit()
                        log("✅ Admin users created in restaurants table")
                    
                    # Check if we need to restore sample restaurants
                    restaurant_count = session.execute(text("""
                        SELECT COUNT(*) FROM restaurants WHERE role = 'owner'
                    """)).scalar()
                    
                    # Check if bella_vista_restaurant exists (the one frontend expects)
                    bella_exists = session.execute(text("""
                        SELECT COUNT(*) FROM restaurants WHERE restaurant_id = 'bella_vista_restaurant'
                    """)).scalar() > 0
                    
                    if restaurant_count == 0 or not bella_exists:
                        # Delete old incorrect restaurant IDs and create proper ones
                        session.execute(text("""
                            DELETE FROM restaurants WHERE restaurant_id IN (
                                'bella_vista', 'ocean_breeze', 'spice_garden', 'mountain_lodge', 'cafe_paris'
                            )
                        """))
                        
                        # Restore sample restaurants with proper IDs that match frontend expectations
                        session.execute(text("""
                            INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode)
                            VALUES 
                            ('bella_vista_restaurant', 'bella2024', 'owner', '{"name": "Bella Vista Restaurant", "description": "Fine dining Italian restaurant"}', 'italian', 'dynamic'),
                            ('ocean_breeze_cafe', 'ocean2024', 'owner', '{"name": "Ocean Breeze Cafe", "description": "Seaside cafe with fresh seafood"}', 'seafood', 'dynamic'),
                            ('spice_garden_restaurant', 'spice2024', 'owner', '{"name": "Spice Garden", "description": "Authentic Asian cuisine"}', 'asian', 'dynamic'),
                            ('mountain_lodge_restaurant', 'lodge2024', 'owner', '{"name": "Mountain Lodge Restaurant", "description": "Rustic dining with mountain views"}', 'american', 'dynamic'),
                            ('cafe_paris_bistro', 'paris2024', 'owner', '{"name": "Cafe Paris", "description": "French bistro and patisserie"}', 'french', 'dynamic'),
                            ('test_restaurant', 'test123', 'owner', '{"name": "Test Restaurant", "description": "Test restaurant for development"}', 'test', 'dynamic'),
                            ('demo_restaurant', 'demo2024', 'owner', '{"name": "Demo Restaurant", "description": "Demo restaurant for testing"}', 'demo', 'dynamic')
                            ON CONFLICT (restaurant_id) DO NOTHING
                        """))
                        session.commit()
                        log("✅ Sample restaurants restored with correct IDs for frontend compatibility")
                    else:
                        log(f"✅ Found {restaurant_count} existing restaurants including bella_vista_restaurant")
                    
                except Exception as admin_error:
                    log(f"⚠️ Restaurant restoration warning: {admin_error}")
                
                session.close()
                log("✅ GSI Bali Agency created successfully in businesses table!")
                log("🎉 GSI is now live and ready for visa inquiries!")
                return True
                
            except Exception as e:
                log(f"⚠️ Businesses table approach failed: {e}")
                try:
                    session.rollback()
                    session.close()
                except:
                    pass
        
        # Fallback to restaurants table
        log("📋 Using fallback approach with restaurants table...")
        try:
            session = SessionLocal()
            
            # Check if GSI exists in restaurants table
            result = session.execute(text("""
                SELECT COUNT(*) FROM restaurants WHERE restaurant_id = 'gsi_bali_agency'
            """))
            
            if result.scalar() > 0:
                log("✅ GSI Bali Agency already exists in restaurants table")
                session.close()
                return True
            
            # Create GSI in restaurants table as fallback
            session.execute(text("""
                INSERT INTO restaurants (restaurant_id, password, role, data)
                VALUES (
                    'gsi_bali_agency',
                    'gsi2025',
                    'owner',
                    '{"name": "GSI Bali Agency", "description": "Professional visa services in Bali", "type": "visa_agency"}'
                )
            """))
            
            session.commit()
            session.close()
            log("✅ GSI Bali Agency created successfully in restaurants table!")
            log("🎉 GSI is now live and ready for visa inquiries!")
            return True
            
        except Exception as e:
            log(f"❌ Fallback also failed: {e}")
            try:
                session.rollback()
                session.close()
            except:
                pass
            return False
            
    except ImportError:
        log("⚠️ Database modules not available (normal in local env)")
        return False
    except Exception as e:
        log(f"❌ Auto-deploy failed: {e}")
        return False

# Run auto-deploy
if __name__ == "__main__":
    auto_deploy_gsi()
