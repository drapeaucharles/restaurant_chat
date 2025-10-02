#!/usr/bin/env python3
"""
Database Investigation and Restoration Script
Connects directly to the database to see what's there and fix it properly
"""

import os
import sys
import json
from sqlalchemy import create_engine, text, MetaData, Table
from sqlalchemy.orm import sessionmaker

# Database URL
DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def log(message):
    print(f"[DB-FIX] {message}")

def investigate_database():
    """Investigate the current state of the database"""
    log("🔍 Investigating database state...")
    
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        with engine.connect() as conn:
            # Check what tables exist
            log("📋 Checking existing tables...")
            result = conn.execute(text("""
                SELECT table_name FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """))
            tables = [row[0] for row in result.fetchall()]
            log(f"Found tables: {tables}")
            
            # Check restaurants table structure if it exists
            if 'restaurants' in tables:
                log("🏪 Analyzing restaurants table...")
                
                # Get column info
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable 
                    FROM information_schema.columns 
                    WHERE table_name = 'restaurants'
                    ORDER BY ordinal_position
                """))
                columns = result.fetchall()
                log("Restaurants table columns:")
                for col in columns:
                    log(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
                
                # Get current restaurant data
                result = conn.execute(text("""
                    SELECT restaurant_id, role, 
                           COALESCE(data->>'name', 'No name') as name,
                           restaurant_category,
                           business_type
                    FROM restaurants 
                    ORDER BY role, restaurant_id
                """))
                restaurants = result.fetchall()
                
                log(f"\n📊 Current restaurants ({len(restaurants)} total):")
                for r in restaurants:
                    log(f"  - {r[0]} ({r[1]}) - {r[2]} [{r[3] or 'no category'}] [{r[4] or 'no type'}]")
            
            # Check businesses table if it exists
            if 'businesses' in tables:
                log("\n🏢 Analyzing businesses table...")
                
                result = conn.execute(text("""
                    SELECT business_id, type, name, role 
                    FROM businesses 
                    ORDER BY type, business_id
                """))
                businesses = result.fetchall()
                
                log(f"Current businesses ({len(businesses)} total):")
                for b in businesses:
                    log(f"  - {b[0]} ({b[1]}) - {b[2]} [{b[3]}]")
            
            # Check for any chat messages to see what restaurants were active
            if 'chat_messages' in tables:
                log("\n💬 Checking chat history for restaurant activity...")
                result = conn.execute(text("""
                    SELECT DISTINCT restaurant_id, COUNT(*) as message_count
                    FROM chat_messages 
                    GROUP BY restaurant_id 
                    ORDER BY message_count DESC
                    LIMIT 10
                """))
                active_restaurants = result.fetchall()
                
                if active_restaurants:
                    log("Restaurants with chat activity:")
                    for r in active_restaurants:
                        log(f"  - {r[0]}: {r[1]} messages")
                else:
                    log("No chat messages found")
            
            # Check for menu items to see what restaurants had menus
            if 'menu_items' in tables:
                log("\n🍽️ Checking menu data...")
                result = conn.execute(text("""
                    SELECT DISTINCT restaurant_id, COUNT(*) as item_count
                    FROM menu_items 
                    GROUP BY restaurant_id 
                    ORDER BY item_count DESC
                """))
                menu_restaurants = result.fetchall()
                
                if menu_restaurants:
                    log("Restaurants with menu data:")
                    for r in menu_restaurants:
                        log(f"  - {r[0]}: {r[1]} menu items")
                else:
                    log("No menu items found")
        
        return True
        
    except Exception as e:
        log(f"❌ Error investigating database: {e}")
        return False

def restore_missing_restaurants():
    """Restore restaurants based on what we find in the database"""
    log("\n🔧 Starting restaurant restoration...")
    
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Get restaurants that have chat activity but don't exist in restaurants table
        missing_restaurants = []
        
        try:
            # Find restaurant IDs mentioned in chat_messages but not in restaurants
            result = session.execute(text("""
                SELECT DISTINCT cm.restaurant_id, COUNT(*) as message_count
                FROM chat_messages cm
                LEFT JOIN restaurants r ON cm.restaurant_id = r.restaurant_id
                WHERE r.restaurant_id IS NULL
                  AND cm.restaurant_id NOT IN ('admin', 'admin@admin.com')
                GROUP BY cm.restaurant_id
                ORDER BY message_count DESC
            """))
            missing_from_chat = result.fetchall()
            
            if missing_from_chat:
                log(f"Found {len(missing_from_chat)} restaurants with chat history but missing from restaurants table:")
                for r in missing_from_chat:
                    log(f"  - {r[0]}: {r[1]} messages")
                    missing_restaurants.append(r[0])
        except Exception as e:
            log(f"⚠️ Could not check chat messages: {e}")
        
        try:
            # Find restaurant IDs mentioned in menu_items but not in restaurants
            result = session.execute(text("""
                SELECT DISTINCT mi.restaurant_id, COUNT(*) as item_count
                FROM menu_items mi
                LEFT JOIN restaurants r ON mi.restaurant_id = r.restaurant_id
                WHERE r.restaurant_id IS NULL
                  AND mi.restaurant_id NOT IN ('admin', 'admin@admin.com')
                GROUP BY mi.restaurant_id
                ORDER BY item_count DESC
            """))
            missing_from_menu = result.fetchall()
            
            if missing_from_menu:
                log(f"Found {len(missing_from_menu)} restaurants with menu data but missing from restaurants table:")
                for r in missing_from_menu:
                    log(f"  - {r[0]}: {r[1]} menu items")
                    if r[0] not in missing_restaurants:
                        missing_restaurants.append(r[0])
        except Exception as e:
            log(f"⚠️ Could not check menu items: {e}")
        
        # Restore missing restaurants
        if missing_restaurants:
            log(f"\n🔧 Restoring {len(missing_restaurants)} missing restaurants...")
            
            for restaurant_id in missing_restaurants:
                try:
                    # Create restaurant with basic data
                    session.execute(text("""
                        INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
                        VALUES (:restaurant_id, :password, 'owner', :data, 'general', 'dynamic', 'restaurant')
                        ON CONFLICT (restaurant_id) DO NOTHING
                    """), {
                        "restaurant_id": restaurant_id,
                        "password": "temp_password_change_me",  # They'll need to reset this
                        "data": json.dumps({
                            "name": restaurant_id.replace("_", " ").title(),
                            "description": f"Restored restaurant: {restaurant_id}",
                            "restored": True,
                            "restoration_date": "2025-10-02"
                        })
                    })
                    log(f"  ✅ Restored: {restaurant_id}")
                except Exception as e:
                    log(f"  ❌ Failed to restore {restaurant_id}: {e}")
            
            session.commit()
            log("✅ Restaurant restoration completed")
        else:
            log("ℹ️ No missing restaurants found to restore")
        
        session.close()
        return True
        
    except Exception as e:
        log(f"❌ Error during restoration: {e}")
        return False

def fix_admin_users():
    """Ensure admin users exist with correct credentials"""
    log("\n🔧 Fixing admin users...")
    
    try:
        engine = create_engine(DATABASE_URL)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        session = SessionLocal()
        
        # Hash function (simplified - in production use proper bcrypt)
        import hashlib
        def simple_hash(password):
            return hashlib.sha256(password.encode()).hexdigest()
        
        admin_users = [
            ("admin", "admin123"),
            ("admin@admin.com", "admin123")
        ]
        
        for admin_id, password in admin_users:
            try:
                # Check if admin exists
                result = session.execute(text("""
                    SELECT COUNT(*) FROM restaurants WHERE restaurant_id = :admin_id
                """), {"admin_id": admin_id})
                
                if result.scalar() == 0:
                    # Create admin user
                    session.execute(text("""
                        INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
                        VALUES (:restaurant_id, :password, 'admin', :data, 'admin', 'dynamic', 'admin')
                    """), {
                        "restaurant_id": admin_id,
                        "password": simple_hash(password),
                        "data": json.dumps({
                            "name": "System Administrator",
                            "business_type": "admin"
                        })
                    })
                    log(f"  ✅ Created admin user: {admin_id}")
                else:
                    log(f"  ✅ Admin user exists: {admin_id}")
            except Exception as e:
                log(f"  ❌ Failed to fix admin {admin_id}: {e}")
        
        session.commit()
        session.close()
        return True
        
    except Exception as e:
        log(f"❌ Error fixing admin users: {e}")
        return False

def main():
    """Main function to investigate and fix the database"""
    log("🚀 Starting database investigation and fix...")
    
    # Step 1: Investigate current state
    if not investigate_database():
        log("❌ Investigation failed, aborting")
        return False
    
    # Step 2: Fix admin users
    if not fix_admin_users():
        log("❌ Admin user fix failed")
        return False
    
    # Step 3: Restore missing restaurants
    if not restore_missing_restaurants():
        log("❌ Restaurant restoration failed")
        return False
    
    # Step 4: Final verification
    log("\n🔍 Final verification...")
    investigate_database()
    
    log("\n🎉 Database investigation and fix completed!")
    return True

if __name__ == "__main__":
    main()
