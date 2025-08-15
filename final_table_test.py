#!/usr/bin/env python3
"""
Final test - the table might already exist!
"""
import requests
import json
import uuid

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("🔍 Final Table Test")
print("=" * 50)

# The migration endpoint has been reporting "Table created" 
# Let's test if it's actually there

print("\n1. Testing chat endpoint (with better error handling)...")
chat_data = {
    "restaurant_id": "bella_vista_restaurant",
    "client_id": str(uuid.uuid4()),
    "sender_type": "client",
    "message": "Hi, what pasta dishes do you have?"
}

response = requests.post(f"{BASE_URL}/chat", json=chat_data, timeout=30)
print(f"Status: {response.status_code}")

if response.status_code == 200:
    result = response.json()
    answer = result.get("answer", "")
    if answer:
        print("✅ CHAT IS WORKING!")
        print(f"Response: {answer[:200]}...")
        print("\n🎉 The table exists and RAG is working!")
    else:
        print("⚠️ Empty response")
elif response.status_code == 500:
    error = response.json().get("detail", "")
    if "menu_embeddings" in error and "does not exist" in error:
        print("❌ Table still doesn't exist")
        print("\n📝 Run this in Railway Dashboard Query tab:")
        print("""
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
""")
    else:
        print(f"Different error: {error[:200]}")
else:
    print(f"Unexpected status: {response.text[:200]}")

print("\n2. Testing migration status endpoint...")
response = requests.get(f"{BASE_URL}/migration/status", timeout=10)
if response.status_code == 200:
    status = response.json()
    print(json.dumps(status, indent=2))

print("\n3. Direct connection info for you to use:")
print("postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway")
print("\nUse this in:")
print("- pgAdmin")
print("- TablePlus") 
print("- DBeaver")
print("- Railway Dashboard")
print("- psql command line")