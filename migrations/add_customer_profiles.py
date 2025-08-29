#!/usr/bin/env python3
"""
Migration to add customer_profiles table
Run this to create the customer profile system
"""
import sys
sys.path.append('..')

from sqlalchemy import create_engine, text
from database import DATABASE_URL, engine
from models.customer_profile import CustomerProfile

def migrate():
    """Create customer_profiles table"""
    print("Creating customer_profiles table...")
    
    try:
        # Create the table
        CustomerProfile.__table__.create(engine, checkfirst=True)
        print("✓ customer_profiles table created successfully!")
        
        # Verify it was created
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'customer_profiles'
                ORDER BY ordinal_position;
            """))
            
            print("\nTable structure:")
            for row in result:
                print(f"  - {row[0]}: {row[1]}")
                
    except Exception as e:
        print(f"❌ Error creating table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("Customer Profile Migration")
    print("=========================")
    print(f"Database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    print("")
    
    if migrate():
        print("\n✅ Migration completed successfully!")
        print("\nThe AI can now remember:")
        print("- Customer names")
        print("- Dietary restrictions") 
        print("- Allergies")
        print("- Preferences")
        print("- Order history")
    else:
        print("\n❌ Migration failed!")