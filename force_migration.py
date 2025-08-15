#!/usr/bin/env python3
"""
Force migration by creating a simpler table
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("🔧 Forcing table creation without pgvector...")

# First, let's drop the existing table if any
drop_sql = """
DROP TABLE IF EXISTS menu_embeddings CASCADE;
"""

# Then create a simple table
create_sql = """
CREATE TABLE IF NOT EXISTS menu_embeddings (
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

CREATE UNIQUE INDEX IF NOT EXISTS idx_menu_embeddings_unique 
ON menu_embeddings(restaurant_id, item_id);

CREATE INDEX IF NOT EXISTS idx_menu_embeddings_restaurant 
ON menu_embeddings(restaurant_id);
"""

print("SQL to run:")
print(drop_sql)
print(create_sql)

print("\n⚠️  You need to run this SQL directly on your Railway PostgreSQL")
print("   1. Go to Railway dashboard")
print("   2. Click on PostgreSQL service")
print("   3. Click 'Connect' → 'psql command'")
print("   4. Run the SQL above")

print("\nOr use Railway CLI:")
print("railway run psql -c \"" + drop_sql.replace('\n', ' ') + "\"")
print("railway run psql -c \"" + create_sql.replace('\n', ' ') + "\"")