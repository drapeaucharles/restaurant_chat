import requests
import uuid
import json

base_url = "https://restaurantchat-production.up.railway.app"

# Test multiple times with different client IDs
for i in range(3):
    client_id = str(uuid.uuid4())
    print(f"\nTest {i+1} - Client ID: {client_id}")
    
    # Test hello
    response = requests.post(
        f"{base_url}/chat",
        json={
            "restaurant_id": "bella_vista_restaurant",
            "client_id": client_id,
            "sender_type": "client",
            "message": "hello"
        }
    )
    
    if response.status_code == 200:
        answer = response.json()['answer']
        print(f"Response: {answer}")
        
        # Check for pasta mentions
        if 'pasta' in answer.lower() or 'spaghetti' in answer.lower():
            print("❌ ERROR: Pasta mentioned in greeting response!")
        else:
            print("✅ OK: No pasta in greeting")
    else:
        print(f"Error: {response.status_code}")

# Also check the deployment info
print("\n" + "="*60)
print("Checking deployment info...")
info_response = requests.get(f"{base_url}/")
if info_response.status_code == 200:
    deployment = info_response.json()['deployment']
    print(f"Version: {deployment['version']}")
    print(f"Timestamp: {deployment['deployment_timestamp']}")
    print(f"Chat service: {deployment['mia_chat_service']}")