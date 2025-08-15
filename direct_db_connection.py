#!/usr/bin/env python3
"""
Direct database connection using urllib and json
"""
import urllib.request
import urllib.parse
import json
import base64
import ssl

# Database connection details
DB_HOST = "shortline.proxy.rlwy.net"
DB_PORT = "31808"
DB_NAME = "railway"
DB_USER = "postgres"
DB_PASS = "pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh"

# Create table SQL
CREATE_TABLE_SQL = """
DROP TABLE IF EXISTS menu_embeddings CASCADE;

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
);

CREATE UNIQUE INDEX idx_menu_embeddings_unique 
ON menu_embeddings(restaurant_id, item_id);

CREATE INDEX idx_menu_embeddings_restaurant 
ON menu_embeddings(restaurant_id);
"""

# Try using the existing database connection through the app
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

try:
    # Import from the project
    from database import engine
    from sqlalchemy import text
    
    print("🔧 Connecting to database via SQLAlchemy...")
    
    with engine.connect() as conn:
        print("✅ Connected!")
        
        # Execute SQL
        for statement in CREATE_TABLE_SQL.split(';'):
            statement = statement.strip()
            if statement:
                print(f"📋 Executing: {statement[:50]}...")
                conn.execute(text(statement))
                conn.commit()
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'menu_embeddings'"))
        count = result.scalar()
        
        if count > 0:
            print("\n✅ SUCCESS! Table 'menu_embeddings' created!")
            
            # Test via API
            import requests
            response = requests.get("https://restaurantchat-production.up.railway.app/migration/status")
            if response.status_code == 200:
                status = response.json()
                print(f"\n📊 Migration Status:")
                print(f"   Table exists: {status.get('table_exists')}")
                print(f"   Ready: {status.get('status')}")
        else:
            print("\n❌ Table creation failed")
            
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()