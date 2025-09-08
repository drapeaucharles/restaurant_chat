#!/usr/bin/env python3
"""Check if the heartbeat endpoint has the bore URL update code"""

import requests
import json

# Test the heartbeat endpoint with a fake request to see if it accepts public_url
test_data = {
    "miner_id": "999",  # Non-existent miner
    "status": "available",
    "public_url": "http://bore.pub:12345"
}

print("Testing heartbeat endpoint to see if it accepts public_url...")
response = requests.post("https://mia-backend-production.up.railway.app/heartbeat", json=test_data)

print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")

# The old version would just say "Miner not found"
# The new version should still say that, but we're checking it accepts the public_url field

print("\nChecking /chat endpoint response format...")
test_chat = {
    "message": "test",
    "context": {}
}

response = requests.post("https://mia-backend-production.up.railway.app/chat", json=test_chat)
result = response.json()

print(f"Chat response keys: {list(result.keys())}")
print(f"Status: {result.get('status')}")

if 'job_id' in result:
    print("✅ New code is deployed (has job_id)")
else:
    print("❌ Old code still running (no job_id)")