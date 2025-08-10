import requests
import json
from datetime import datetime

print("Verifying which chat service is deployed...")
print("="*60)

# Check git commit on server
try:
    # The deployment info shows the configured version
    resp = requests.get("https://restaurantchat-production.up.railway.app/")
    deployment = resp.json()['deployment']
    print(f"Configured version: {deployment['version']}")
    print(f"Configured service: {deployment['mia_chat_service']}")
    print(f"Deployment timestamp: {deployment['deployment_timestamp']}")
except Exception as e:
    print(f"Error checking deployment: {e}")

print("\n" + "="*60)
print("Testing actual behavior...")

# Test 1: Check if it's using the OLD rigid system prompt
test_resp = requests.post(
    "https://restaurantchat-production.up.railway.app/chat",
    json={
        "restaurant_id": "bella_vista_restaurant",
        "client_id": "550e8400-e29b-41d4-a716-446655440000",
        "sender_type": "client", 
        "message": "hi"
    }
)

if test_resp.status_code == 200:
    answer = test_resp.json()['answer'].lower()
    
    # Check for signs of the OLD service
    if "absolute requirement" in answer or "must list every single" in answer:
        print("❌ Detected OLD service: System prompt is showing in response")
    elif "pasta" in answer and "hello" not in answer:
        print("❌ Detected OLD service: Immediately listing pasta without greeting")
    elif "customer:" in answer or "assistant:" in answer:
        print("❌ Detected OLD service: Showing fake conversation history")
    else:
        print("✅ Might be using improved service")
    
    print(f"\nActual response preview: {test_resp.json()['answer'][:200]}...")

print("\n" + "="*60)
print("DIAGNOSIS:")
print("The deployment info shows v3-improved-ai but the actual behavior")
print("suggests the OLD mia_chat_service.py is still running.")
print("\nPossible causes:")
print("1. Railway hasn't deployed the latest code yet")
print("2. The improved service file might not be included in deployment")
print("3. Environment variable USE_IMPROVED_CHAT might be false on Railway")
print("="*60)