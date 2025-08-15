#!/usr/bin/env python3
"""
Fix table structure via API
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("🔧 Attempting to fix table via API...")

# First check current status
print("\n1. Checking current migration status...")
response = requests.get(f"{BASE_URL}/migration/status")
if response.status_code == 200:
    status = response.json()
    print(f"   pgvector_installed: {status.get('pgvector_installed')}")
    print(f"   table_exists: {status.get('table_exists')}")
    print(f"   embedding_count: {status.get('embedding_count')}")
    print(f"   status: {status.get('status')}")

# Try to run migration again
print("\n2. Running migration via API...")
migration_data = {
    "secret_key": "your-secret-migration-key"
}

response = requests.post(
    f"{BASE_URL}/migration/run-pgvector",
    json=migration_data,
    timeout=30
)

if response.status_code == 200:
    result = response.json()
    print(f"   Status: {result.get('status')}")
    print(f"   Message: {result.get('message')}")
    if result.get('table_created'):
        print("   ✅ Table created successfully!")

# Create a test embedding endpoint if needed
print("\n3. Testing if we can bypass and index directly...")

# Let's check the restaurant data first
print("\n4. Getting restaurant menu data...")
response = requests.get(f"{BASE_URL}/restaurant/bella_vista_restaurant")
if response.status_code == 200:
    restaurant = response.json()
    menu_items = restaurant.get('menu', [])
    print(f"   Found {len(menu_items)} menu items")
    
    # Show first few items
    for item in menu_items[:3]:
        print(f"   - {item.get('dish', 'Unknown')}: {item.get('price', 'N/A')}")

print("\n📝 Next Steps:")
print("Since I cannot directly access the database from here, you need to:")
print("\n1. Install Railway CLI if you haven't:")
print("   npm install -g @railway/cli")
print("\n2. Login and link to your project:")
print("   railway login")
print("   railway link")
print("\n3. Run this command to create the table:")
print('   railway run psql -c "CREATE TABLE IF NOT EXISTS menu_embeddings (id SERIAL PRIMARY KEY, restaurant_id VARCHAR(255) NOT NULL, item_id VARCHAR(255) NOT NULL, item_name VARCHAR(255) NOT NULL, item_description TEXT, item_price VARCHAR(50), item_category VARCHAR(100), item_ingredients TEXT, dietary_tags TEXT, full_text TEXT NOT NULL, embedding_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)"')
print("\n4. Then index your menu:")
print("   railway run python index_menu_local.py bella_vista_restaurant")

print("\n🔗 Your database connection info:")
print("   Host: shortline.proxy.rlwy.net")
print("   Port: 31808")
print("   Database: railway")
print("   Username: postgres")
print("   Password: pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh")