#!/usr/bin/env python3
"""
Direct database migration
"""
import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

# Get database URL
DATABASE_URL = os.getenv("DATABASE_URL")

print("🔧 Running direct database migration...")

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("✅ Connected to database")
    
    # Try to create pgvector extension (might fail)
    try:
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.commit()
        print("✅ pgvector extension created")
    except Exception as e:
        conn.rollback()
        print(f"⚠️  pgvector not available: {str(e)[:100]}")
        print("   Will create table without vector column")
    
    # Create table without vector column if pgvector not available
    try:
        # First, drop the table if it exists
        cur.execute("DROP TABLE IF EXISTS menu_embeddings")
        
        # Create table without vector column
        cur.execute("""
            CREATE TABLE menu_embeddings (
                id SERIAL PRIMARY KEY,
                restaurant_id VARCHAR(255) NOT NULL,
                item_id VARCHAR(255) NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                item_description TEXT,
                item_price VARCHAR(50),
                item_category VARCHAR(100),
                item_ingredients JSONB,
                dietary_tags JSONB,
                full_text TEXT NOT NULL,
                embedding_json TEXT,  -- Store as JSON text instead of vector
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(restaurant_id, item_id)
            )
        """)
        
        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_menu_embeddings_restaurant 
            ON menu_embeddings(restaurant_id)
        """)
        
        conn.commit()
        print("✅ Table created successfully (without vector column)")
        
        # Check if table was created
        cur.execute("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'menu_embeddings'
        """)
        exists = cur.fetchone()[0] > 0
        print(f"✅ Table exists: {exists}")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ Error creating table: {e}")
        raise
    
    # Close connection
    cur.close()
    conn.close()
    
    print("\n🎉 Migration completed successfully!")
    print("   Table created without pgvector support")
    print("   Will use JSON storage for embeddings")
    
except Exception as e:
    print(f"❌ Migration failed: {e}")
    raise