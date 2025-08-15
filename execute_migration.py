#!/usr/bin/env python3
"""
Execute migration directly using the database URL
"""
import os
import sys
import subprocess

# Install psycopg2-binary if not available
try:
    import psycopg2
except ImportError:
    print("Installing psycopg2-binary...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psycopg2-binary"])
    import psycopg2

from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

print("🔧 Connecting to database...")

try:
    # Connect to database
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    print("✅ Connected successfully!")
    
    # Drop existing table
    print("\n📋 Dropping existing table if any...")
    cur.execute("DROP TABLE IF EXISTS menu_embeddings CASCADE")
    conn.commit()
    print("✅ Dropped existing table")
    
    # Create new table
    print("\n📋 Creating menu_embeddings table...")
    create_table_sql = """
    CREATE TABLE menu_embeddings (
        id SERIAL PRIMARY KEY,
        restaurant_id VARCHAR(255) NOT NULL,
        item_id VARCHAR(255) NOT NULL,
        item_name VARCHAR(255) NOT NULL,
        item_description TEXT,
        item_price VARCHAR(50),
        item_category VARCHAR(100),
        item_ingredients TEXT,
        dietary_tags TEXT,
        full_text TEXT NOT NULL,
        embedding_json TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """
    cur.execute(create_table_sql)
    conn.commit()
    print("✅ Table created")
    
    # Create indexes
    print("\n📋 Creating indexes...")
    cur.execute("""
        CREATE UNIQUE INDEX idx_menu_embeddings_unique 
        ON menu_embeddings(restaurant_id, item_id)
    """)
    
    cur.execute("""
        CREATE INDEX idx_menu_embeddings_restaurant 
        ON menu_embeddings(restaurant_id)
    """)
    conn.commit()
    print("✅ Indexes created")
    
    # Verify table exists
    print("\n📋 Verifying table...")
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'menu_embeddings'
        ORDER BY ordinal_position
    """)
    
    columns = cur.fetchall()
    print("✅ Table structure:")
    for col_name, col_type in columns:
        print(f"   - {col_name}: {col_type}")
    
    # Check if table is empty
    cur.execute("SELECT COUNT(*) FROM menu_embeddings")
    count = cur.fetchone()[0]
    print(f"\n✅ Table has {count} rows (empty, ready for indexing)")
    
    # Close connection
    cur.close()
    conn.close()
    
    print("\n🎉 Migration completed successfully!")
    print("   The menu_embeddings table is ready")
    print("   Next step: Index your menu items")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()