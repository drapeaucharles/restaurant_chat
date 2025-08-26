"""
Manual migration script to add business_type column
Run this directly on Railway using: python manual_migration.py
"""
import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

print(f"Connecting to database...")

# Create engine
engine = create_engine(DATABASE_URL)

try:
    with engine.connect() as conn:
        # Check if column exists
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='restaurants' AND column_name='business_type'
        """))
        
        if result.fetchone():
            print("business_type column already exists - skipping migration")
        else:
            print("Adding business_type column...")
            
            # Add the column
            conn.execute(text("""
                ALTER TABLE restaurants 
                ADD COLUMN business_type VARCHAR DEFAULT 'restaurant'
            """))
            
            # Update existing records
            conn.execute(text("""
                UPDATE restaurants 
                SET business_type = COALESCE(
                    CAST(data->>'business_type' AS VARCHAR),
                    'restaurant'
                )
                WHERE business_type IS NULL
            """))
            
            conn.commit()
            print("Successfully added business_type column!")
            
except Exception as e:
    print(f"Error: {str(e)}")
    exit(1)

print("Migration complete!")