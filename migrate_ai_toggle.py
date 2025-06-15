"""
Database Migration Script for AI Toggle Feature
This script ensures the ai_enabled column exists in the chat_logs table.
"""

import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def run_migration():
    """Run the database migration to add ai_enabled column if it doesn't exist."""
    
    # Get database URL from environment
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Check if column exists
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='chat_logs' AND column_name='ai_enabled'
            """))
            
            column_exists = result.fetchone() is not None
            
            if column_exists:
                print("✅ ai_enabled column already exists in chat_logs table")
                return True
            else:
                print("🔧 Adding ai_enabled column to chat_logs table...")
                
                # Add the column
                conn.execute(text("""
                    ALTER TABLE chat_logs 
                    ADD COLUMN IF NOT EXISTS ai_enabled BOOLEAN DEFAULT TRUE
                """))
                conn.commit()
                
                print("✅ Successfully added ai_enabled column to chat_logs table")
                return True
                
    except Exception as e:
        print(f"❌ Migration failed: {str(e)}")
        return False

def verify_migration():
    """Verify that the migration was successful."""
    
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        print("❌ DATABASE_URL not found in environment variables")
        return False
    
    try:
        engine = create_engine(database_url)
        
        with engine.connect() as conn:
            # Check all columns in chat_logs table
            result = conn.execute(text("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns 
                WHERE table_name='chat_logs'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            
            print("\n📋 Current chat_logs table structure:")
            for col in columns:
                print(f"  - {col[0]} ({col[1]}) default: {col[2]}")
            
            # Specifically check for ai_enabled
            ai_enabled_col = next((col for col in columns if col[0] == 'ai_enabled'), None)
            
            if ai_enabled_col:
                print(f"\n✅ ai_enabled column verified: {ai_enabled_col[1]} with default {ai_enabled_col[2]}")
                return True
            else:
                print("\n❌ ai_enabled column not found")
                return False
                
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting AI Toggle Feature Migration...")
    
    # Run migration
    migration_success = run_migration()
    
    if migration_success:
        # Verify migration
        verification_success = verify_migration()
        
        if verification_success:
            print("\n🎉 Migration completed successfully!")
            print("\n📝 Next steps:")
            print("1. Deploy the updated backend code")
            print("2. Test the AI toggle functionality")
            print("3. Verify frontend integration")
        else:
            print("\n⚠️ Migration completed but verification failed")
    else:
        print("\n❌ Migration failed")

