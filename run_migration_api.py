#!/usr/bin/env python3
"""
Run database migration via API
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("🔧 Running database migration via API...")
print("=" * 50)

# First, let's create a simple endpoint to run the migration
# For now, let's try to connect directly if possible

print("\n📝 Migration SQL:")
migration_sql = """
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create menu_embeddings table
CREATE TABLE IF NOT EXISTS menu_embeddings (
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
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(restaurant_id, item_id)
);

CREATE INDEX idx_menu_embeddings_restaurant ON menu_embeddings(restaurant_id);
CREATE INDEX idx_menu_embeddings_embedding ON menu_embeddings USING ivfflat (embedding vector_cosine_ops);
"""

print(migration_sql)

print("\n⚠️  To run this migration, you need to:")
print("1. Install Railway CLI: npm install -g @railway/cli")
print("2. Login: railway login")
print("3. Link project: railway link")
print("4. Run: railway run python run_migrations.py")
print("\nOR")
print("\n1. Connect to your Railway PostgreSQL database")
print("2. Run the SQL above manually")

print("\n💡 Alternative: Let me check if there's a migration endpoint...")

# Check if there's a migration endpoint
response = requests.get(f"{BASE_URL}/docs")
if response.status_code == 200:
    print("\n✅ API docs available at: https://restaurantchat-production.up.railway.app/docs")
    print("   Check if there's a migration endpoint there.")