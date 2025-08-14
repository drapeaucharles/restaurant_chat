#!/usr/bin/env python3
"""
Run migration via API endpoint
"""
import requests
import time
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

print("⏳ Waiting for deployment...")
for i in range(60):  # Wait up to 5 minutes
    try:
        response = requests.get(f"{BASE_URL}/migration/status", timeout=5)
        if response.status_code == 200:
            print("✅ Migration endpoint deployed!")
            break
    except:
        pass
    time.sleep(5)
    print(".", end="", flush=True)

print("\n\n🔧 Running migration...")

# Run the migration with secret key
migration_data = {
    "secret_key": "your-secret-migration-key"
}

response = requests.post(
    f"{BASE_URL}/migration/run-pgvector",
    json=migration_data,
    timeout=30
)

if response.status_code == 200:
    data = response.json()
    print(f"\n✅ Migration result:")
    print(json.dumps(data, indent=2))
else:
    print(f"\n❌ Migration failed: {response.status_code}")
    print(response.text)

# Check final status
print("\n📊 Checking migration status...")
response = requests.get(f"{BASE_URL}/migration/status")
if response.status_code == 200:
    status = response.json()
    print(json.dumps(status, indent=2))
    
    if status.get("status") == "ready":
        print("\n🎉 Migration complete! RAG system ready for indexing.")
        print("\nNext step: Run indexing")
        print("curl -X POST https://restaurantchat-production.up.railway.app/embeddings/index/bella_vista_restaurant")
    else:
        print("\n⚠️  Migration partially complete. Check Railway logs for details.")