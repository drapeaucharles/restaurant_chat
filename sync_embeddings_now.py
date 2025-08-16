#!/usr/bin/env python3
"""
Sync embeddings for restaurants that need it
Using the admin API endpoints
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://restaurantchat-production.up.railway.app"

# You mentioned you have admin credentials for frontend
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "Lol007321lol!"

def get_admin_token():
    """Login as admin to get token"""
    print("🔐 Logging in as admin...")
    
    response = requests.post(
        f"{BASE_URL}/restaurant/login",
        json={
            "restaurant_id": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if response.status_code == 200:
        data = response.json()
        token = data.get("access_token")
        print("✅ Login successful")
        return token
    else:
        print(f"❌ Login failed: {response.status_code}")
        print(response.text)
        return None

def sync_all_restaurants(token):
    """Initialize embeddings for all restaurants"""
    print("\n🔄 Initializing embeddings for all restaurants...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.post(
        f"{BASE_URL}/embeddings/admin/initialize-all",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Batch initialization complete!")
        print(f"   Total restaurants processed: {data.get('total_restaurants', 0)}")
        print(f"   Total embeddings created: {data.get('total_indexed', 0)}")
        
        # Show results
        if 'results' in data:
            print("\n📊 Detailed Results:")
            for result in data['results']:
                status_icon = "✅" if result['status'] == 'success' else "❌"
                print(f"   {status_icon} {result['restaurant_id']}: {result['status']}")
                if 'indexed' in result:
                    print(f"      Created {result['indexed']} embeddings")
                elif 'error' in result:
                    print(f"      Error: {result['error']}")
                elif 'reason' in result:
                    print(f"      Skipped: {result['reason']}")
        
        return True
    else:
        print(f"❌ Failed to initialize embeddings: {response.status_code}")
        print(response.text)
        return False

def check_final_status(token):
    """Check embedding status after sync"""
    print("\n📊 Checking final embedding status...")
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    response = requests.get(
        f"{BASE_URL}/embeddings/admin/status",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        summary = data.get('summary', {})
        
        print(f"\n✅ Final Status:")
        print(f"   Total restaurants: {summary.get('total_restaurants', 0)}")
        print(f"   Fully indexed: {summary.get('fully_indexed', 0)}")
        print(f"   Need sync: {summary.get('needs_sync', 0)}")
        print(f"   Percentage indexed: {summary.get('percentage_indexed', 0)}%")
        
        if 'restaurants' in data:
            print("\n📋 Restaurant Details:")
            for r in data['restaurants']:
                status = "✅" if r['fully_indexed'] else "⚠️"
                print(f"   {status} {r['restaurant_name']} ({r['restaurant_id']})")
                print(f"      Menu items: {r['menu_count']}, Embeddings: {r['embedding_count']}")
    else:
        print(f"❌ Failed to get status: {response.status_code}")

def sync_specific_restaurants(token):
    """Sync specific restaurants that need it"""
    restaurants_to_sync = [
        "Test",
        "Labrisa", 
        "RestoLorenzo",
        "RestoBulla"
    ]
    
    headers = {
        "Authorization": f"Bearer {token}"
    }
    
    print("\n🔧 Syncing specific restaurants...")
    
    for restaurant_id in restaurants_to_sync:
        print(f"\n   Syncing {restaurant_id}...")
        
        response = requests.post(
            f"{BASE_URL}/embeddings/admin/initialize/{restaurant_id}",
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ {data.get('message', 'Success')}")
            if 'indexed' in data:
                print(f"      Created {data['indexed']} embeddings")
        else:
            print(f"   ❌ Failed: {response.status_code}")

def main():
    print("🚀 EMBEDDING SYNC TOOL")
    print("=" * 60)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Get admin token
    token = get_admin_token()
    if not token:
        print("❌ Failed to authenticate. Exiting.")
        return
    
    # Try batch sync first
    success = sync_all_restaurants(token)
    
    if not success:
        # If batch fails, try individual restaurants
        print("\n⚠️  Batch sync failed. Trying individual restaurants...")
        sync_specific_restaurants(token)
    
    # Check final status
    check_final_status(token)
    
    print("\n✅ Sync process complete!")

if __name__ == "__main__":
    main()