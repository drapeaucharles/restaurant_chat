#!/usr/bin/env python3
"""
Execute migration using SQLAlchemy
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

print("🔧 Connecting to database using SQLAlchemy...")

try:
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("✅ Connected successfully!")
        
        # Drop existing table
        print("\n📋 Dropping existing table if any...")
        conn.execute(text("DROP TABLE IF EXISTS menu_embeddings CASCADE"))
        conn.commit()
        print("✅ Dropped existing table")
        
        # Create new table
        print("\n📋 Creating menu_embeddings table...")
        create_table_sql = text("""
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
        """)
        conn.execute(create_table_sql)
        conn.commit()
        print("✅ Table created")
        
        # Create indexes
        print("\n📋 Creating indexes...")
        conn.execute(text("""
            CREATE UNIQUE INDEX idx_menu_embeddings_unique 
            ON menu_embeddings(restaurant_id, item_id)
        """))
        
        conn.execute(text("""
            CREATE INDEX idx_menu_embeddings_restaurant 
            ON menu_embeddings(restaurant_id)
        """))
        conn.commit()
        print("✅ Indexes created")
        
        # Verify table exists
        print("\n📋 Verifying table...")
        result = conn.execute(text("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_name = 'menu_embeddings'
            ORDER BY ordinal_position
        """))
        
        columns = result.fetchall()
        print("✅ Table structure:")
        for col_name, col_type in columns:
            print(f"   - {col_name}: {col_type}")
        
        # Check if table is empty
        result = conn.execute(text("SELECT COUNT(*) FROM menu_embeddings"))
        count = result.scalar()
        print(f"\n✅ Table has {count} rows (empty, ready for indexing)")
    
    print("\n🎉 Migration completed successfully!")
    print("   The menu_embeddings table is ready")
    print("   Next step: Index your menu items")
    
    # Test the deployment
    print("\n🔍 Testing deployment...")
    import requests
    
    # Check migration status
    response = requests.get("https://restaurantchat-production.up.railway.app/migration/status")
    if response.status_code == 200:
        status = response.json()
        print(f"✅ Migration status: {status}")
    
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()