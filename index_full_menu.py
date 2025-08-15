"""
Re-index all 50 menu items for bella_vista_restaurant
"""
import requests
import json
import time

BASE_URL = "https://mia-chat-backend-production.up.railway.app"

def index_full_menu():
    """Index all menu items"""
    print("Indexing full menu (50 items) for bella_vista_restaurant...")
    
    payload = {
        "restaurant_id": "bella_vista_restaurant"
    }
    
    try:
        response = requests.post(
            f"{BASE_URL}/rag/index",
            json=payload,
            timeout=120  # Longer timeout for 50 items
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"Success! {result}")
            return True
        else:
            print(f"Error: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"Exception: {str(e)}")
        return False

if __name__ == "__main__":
    # First check if the API is available
    print("Checking API availability...")
    try:
        health = requests.get(f"{BASE_URL}/health", timeout=5)
        if health.status_code != 200:
            print("API not available yet. Waiting...")
            time.sleep(30)
    except:
        print("API not responding. Waiting...")
        time.sleep(30)
    
    # Now index
    if index_full_menu():
        print("\nFull menu indexed successfully!")
        print("You can now run the comprehensive test.")
    else:
        print("\nIndexing failed. Please check the deployment.")