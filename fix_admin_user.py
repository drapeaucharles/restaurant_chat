#!/usr/bin/env python3
"""
Fix admin user role in production database
Run this on Railway using: railway run python fix_admin_user.py
"""
import os
import sys

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from database import DATABASE_URL
import models
from auth import hash_password

def fix_admin_user():
    """Update admin user to have correct role"""
    # Create engine with the database URL
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    
    try:
        # First, check what admin users exist
        print("Checking for admin users...")
        
        # Raw SQL to see all potential admin users
        result = db.execute(text("""
            SELECT restaurant_id, role, data
            FROM restaurants 
            WHERE restaurant_id IN ('admin', 'admin@admin.com')
            OR role = 'admin'
        """))
        
        print("\nFound users:")
        for row in result:
            print(f"  - ID: {row[0]}, Role: {row[1]}, Data: {row[2]}")
        
        # Update or create the 'admin' user
        print("\nUpdating/creating 'admin' user...")
        
        # Check if 'admin' exists
        admin_exists = db.execute(text("""
            SELECT COUNT(*) FROM restaurants WHERE restaurant_id = 'admin'
        """)).scalar()
        
        if admin_exists:
            # Update existing admin
            db.execute(text("""
                UPDATE restaurants 
                SET role = 'admin',
                    password = :password,
                    data = :data
                WHERE restaurant_id = 'admin'
            """), {
                'password': hash_password("Lol007321lol!"),
                'data': '{"name": "System Administrator", "business_type": "admin"}'
            })
            print("✅ Updated 'admin' user")
        else:
            # Create new admin
            db.execute(text("""
                INSERT INTO restaurants (restaurant_id, password, role, data)
                VALUES ('admin', :password, 'admin', :data)
            """), {
                'password': hash_password("Lol007321lol!"),
                'data': '{"name": "System Administrator", "business_type": "admin"}'
            })
            print("✅ Created 'admin' user")
        
        db.commit()
        
        # Verify the change
        result = db.execute(text("""
            SELECT restaurant_id, role FROM restaurants WHERE restaurant_id = 'admin'
        """)).first()
        
        if result:
            print(f"\n✅ Verified: admin user has role '{result[1]}'")
        else:
            print("\n❌ Error: admin user not found after update")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_admin_user()