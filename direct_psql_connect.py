#!/usr/bin/env python3
"""
Direct PostgreSQL connection using subprocess and psql
"""
import subprocess
import os

# Database URL
DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

# SQL commands
SQL_COMMANDS = """
-- Drop existing table
DROP TABLE IF EXISTS menu_embeddings CASCADE;

-- Create table
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

-- Create indexes
CREATE UNIQUE INDEX idx_menu_embeddings_unique ON menu_embeddings(restaurant_id, item_id);
CREATE INDEX idx_menu_embeddings_restaurant ON menu_embeddings(restaurant_id);

-- Verify
SELECT 'Table created successfully!' as status, COUNT(*) as row_count FROM menu_embeddings;
"""

print("🔧 Connecting to PostgreSQL directly...")

try:
    # Use psql command
    result = subprocess.run(
        ['psql', DATABASE_URL, '-c', SQL_COMMANDS],
        capture_output=True,
        text=True,
        check=True
    )
    
    print("✅ SUCCESS!")
    print(result.stdout)
    
except subprocess.CalledProcessError as e:
    print(f"❌ Error: {e}")
    print(f"stdout: {e.stdout}")
    print(f"stderr: {e.stderr}")
except FileNotFoundError:
    print("❌ psql command not found")
    print("Trying alternative approach...")
    
    # Write SQL to file and try again
    with open('create_table.sql', 'w') as f:
        f.write(SQL_COMMANDS)
    
    # Try using Python's built-in database support
    import socket
    import ssl
    
    print("\n📡 Attempting raw PostgreSQL connection...")
    
    # Parse connection string
    # postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway
    host = "shortline.proxy.rlwy.net"
    port = 31808
    user = "postgres"
    password = "pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh"
    database = "railway"
    
    # This would require PostgreSQL protocol implementation
    print(f"Host: {host}")
    print(f"Port: {port}")
    print(f"Database: {database}")
    print(f"User: {user}")
    
    print("\n📝 Since psql is not available, use one of these methods:")
    print("\n1. Use any PostgreSQL client (pgAdmin, DBeaver, TablePlus) with:")
    print(f"   {DATABASE_URL}")
    print("\n2. Use Railway CLI:")
    print("   railway run psql -c \"$(cat create_table.sql)\"")
    print("\n3. Use the web interface at railway.app")