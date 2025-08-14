#!/usr/bin/env python3
"""
Check if pgvector is available and working
"""
from sqlalchemy import text
from database import engine
import sys

def check_pgvector():
    """Check pgvector availability"""
    print("🔍 Checking pgvector status...")
    
    with engine.connect() as conn:
        # Check if extension exists
        result = conn.execute(text("""
            SELECT COUNT(*) FROM pg_available_extensions 
            WHERE name = 'vector'
        """)).scalar()
        
        if result > 0:
            print("✅ pgvector extension is available")
        else:
            print("❌ pgvector extension is NOT available")
            print("   Railway PostgreSQL might not have pgvector installed")
            return False
        
        # Check if extension is created
        result = conn.execute(text("""
            SELECT COUNT(*) FROM pg_extension 
            WHERE extname = 'vector'
        """)).scalar()
        
        if result > 0:
            print("✅ pgvector extension is enabled")
        else:
            print("⚠️  pgvector extension is available but not enabled")
            print("   Trying to enable it...")
            
            try:
                conn.execute(text("CREATE EXTENSION vector"))
                conn.commit()
                print("✅ Successfully enabled pgvector!")
            except Exception as e:
                print(f"❌ Failed to enable pgvector: {e}")
                print("\nTo fix this, you need to:")
                print("1. Connect to your Railway PostgreSQL")
                print("2. Run: CREATE EXTENSION vector;")
                return False
        
        # Check if embeddings table exists
        result = conn.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'menu_embeddings'
        """)).scalar()
        
        if result > 0:
            print("✅ menu_embeddings table exists")
            
            # Count existing embeddings
            count = conn.execute(text("""
                SELECT COUNT(*) FROM menu_embeddings
            """)).scalar()
            print(f"📊 Total embeddings: {count}")
        else:
            print("⚠️  menu_embeddings table does not exist")
            print("   Run: python run_migrations.py")
        
        return True

if __name__ == "__main__":
    if check_pgvector():
        print("\n✅ pgvector is ready to use!")
        sys.exit(0)
    else:
        print("\n❌ pgvector setup incomplete")
        sys.exit(1)