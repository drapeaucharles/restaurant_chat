#!/usr/bin/env python3
"""
Ensure admin user exists with correct credentials
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from database import SessionLocal
import models
from auth import hash_password

def ensure_admin_user():
    """Create or update admin user"""
    db = SessionLocal()
    
    try:
        # Check if admin exists
        admin = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == "admin"
        ).first()
        
        if not admin:
            # Create admin user
            admin = models.Restaurant(
                restaurant_id="admin",
                password=hash_password("Lol007321lol!"),
                role="admin",
                data={
                    "name": "System Administrator",
                    "business_type": "admin"
                }
            )
            db.add(admin)
            db.commit()
            print("✅ Created admin user")
        else:
            # Update password and role to ensure they're correct
            admin.password = hash_password("Lol007321lol!")
            admin.role = "admin"
            if not admin.data:
                admin.data = {}
            admin.data["name"] = "System Administrator"
            admin.data["business_type"] = "admin"
            db.commit()
            print("✅ Updated admin user")
            
        # Also check for admin@admin.com
        admin_email = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == "admin@admin.com"
        ).first()
        
        if admin_email:
            print(f"ℹ️  Found admin@admin.com with role: {admin_email.role}")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    ensure_admin_user()