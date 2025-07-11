#!/usr/bin/env python3
"""
Manual migration script to add restaurant_categories column.
Run this script to update the database schema.
"""

import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL environment variable not set")
    sys.exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

# Migration SQL
migration_sql = """
-- Add restaurant_categories column to restaurants table
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS restaurant_categories JSON DEFAULT '[]';
"""

# Run migration
try:
    with engine.connect() as conn:
        print("Running migration to add restaurant_categories column...")
        conn.execute(text(migration_sql))
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify the column was added
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'restaurants' 
            AND column_name = 'restaurant_categories'
        """))
        
        if result.fetchone():
            print("✅ Verified: restaurant_categories column exists")
        else:
            print("❌ Warning: Column may not have been created")
            
except Exception as e:
    print(f"❌ Migration failed: {e}")
    sys.exit(1)