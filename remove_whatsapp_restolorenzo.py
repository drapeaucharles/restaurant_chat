#!/usr/bin/env python3
"""Remove WhatsApp configuration from RestoLorenzo"""
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv
import json

# Load environment variables
load_dotenv()

# Database connection
DATABASE_URL = os.getenv('DATABASE_URL')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def remove_whatsapp_from_restolorenzo():
    """Remove WhatsApp configuration from RestoLorenzo"""
    db = SessionLocal()
    
    try:
        # First, find RestoLorenzo
        result = db.execute(
            text("SELECT * FROM restaurants WHERE business_name = :name"),
            {"name": "RestoLorenzo"}
        )
        restaurant = result.fetchone()
        
        if not restaurant:
            print("❌ RestoLorenzo not found in database")
            return
        
        print(f"✅ Found RestoLorenzo (ID: {restaurant.restaurant_id})")
        
        # Check current whatsapp_config
        print(f"\nCurrent WhatsApp config: {restaurant.whatsapp_config}")
        
        # Remove WhatsApp configuration
        db.execute(
            text("""
                UPDATE restaurants 
                SET whatsapp_config = NULL,
                    updated_at = CURRENT_TIMESTAMP
                WHERE restaurant_id = :id
            """),
            {"id": restaurant.restaurant_id}
        )
        
        # Also check if there's data in the JSON column
        if hasattr(restaurant, 'data') and restaurant.data:
            data = json.loads(restaurant.data) if isinstance(restaurant.data, str) else restaurant.data
            if 'whatsapp' in data:
                del data['whatsapp']
                db.execute(
                    text("""
                        UPDATE restaurants 
                        SET data = :data
                        WHERE restaurant_id = :id
                    """),
                    {"id": restaurant.restaurant_id, "data": json.dumps(data)}
                )
                print("✅ Also removed WhatsApp from data JSON")
        
        # Commit the changes
        db.commit()
        print("\n✅ WhatsApp configuration removed from RestoLorenzo")
        
        # Verify the change
        result = db.execute(
            text("SELECT whatsapp_config FROM restaurants WHERE restaurant_id = :id"),
            {"id": restaurant.restaurant_id}
        )
        updated = result.fetchone()
        print(f"Verification - WhatsApp config is now: {updated.whatsapp_config}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    print("🔧 Removing WhatsApp from RestoLorenzo...\n")
    remove_whatsapp_from_restolorenzo()