#!/usr/bin/env python3
"""
Create table using the deployed API migration endpoint
"""
import requests
import time
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("🔧 Creating table via deployed API...")

# Wait for latest deployment
print("\n⏳ Checking deployment status...")
for i in range(30):
    try:
        response = requests.get(f"{BASE_URL}/", timeout=5)
        if response.status_code == 200:
            print("✅ API is ready")
            break
    except:
        pass
    time.sleep(2)
    print(".", end="", flush=True)

# Run migration multiple times to ensure it works
print("\n\n📋 Running migration...")
for attempt in range(3):
    print(f"\nAttempt {attempt + 1}...")
    
    migration_data = {
        "secret_key": "your-secret-migration-key"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/migration/run-pgvector",
            json=migration_data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            if "table created" in result.get("message", "").lower() or result.get("table_created"):
                print("\n✅ Table created successfully!")
                break
    except Exception as e:
        print(f"Error: {e}")
    
    time.sleep(2)

# Check final status
print("\n\n📊 Checking final status...")
response = requests.get(f"{BASE_URL}/migration/status")
if response.status_code == 200:
    status = response.json()
    print(json.dumps(status, indent=2))
    
    if status.get("table_exists"):
        print("\n🎉 SUCCESS! Table exists and is ready!")
        
        # Test chat
        print("\n💬 Testing chat...")
        chat_data = {
            "restaurant_id": "bella_vista_restaurant",
            "client_id": "550e8400-e29b-41d4-a716-446655440000",
            "sender_type": "client",
            "message": "What pasta dishes do you have?"
        }
        
        response = requests.post(f"{BASE_URL}/chat", json=chat_data, timeout=30)
        if response.status_code == 200:
            result = response.json()
            answer = result.get("answer", "")
            if answer:
                print("✅ Chat is working!")
                print(f"Response: {answer[:200]}...")
            else:
                print("⚠️ Empty response")
        else:
            print(f"Chat error: {response.status_code}")
            print(response.text[:200])
    else:
        print("\n⚠️ Table still not detected. Manual creation needed.")
        print("\nPlease run this SQL in Railway:")
        print("""
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(restaurant_id, item_id)
);
""")