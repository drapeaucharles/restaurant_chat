#!/usr/bin/env python3
"""Delete dummy restaurants NOW"""
import requests
import time

BASE_URL = "https://restaurantchat-production.up.railway.app"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "Lol007321lol!"

# Login
print("🔐 Logging in as admin...")
response = requests.post(
    f"{BASE_URL}/restaurant/login",
    json={"restaurant_id": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
)

if response.status_code != 200:
    print("❌ Login failed")
    exit()

token = response.json()['access_token']
headers = {"Authorization": f"Bearer {token}"}
print("✅ Logged in successfully")

# Restaurants to delete
dummy_restaurants = ["Test", "Labrisa", "RestoLorenzo"]

print("\n🗑️  DELETING DUMMY RESTAURANTS NOW")
print("=" * 60)

for restaurant_id in dummy_restaurants:
    print(f"\n❌ Deleting {restaurant_id}...")
    
    # Try the admin endpoint
    delete_response = requests.delete(
        f"{BASE_URL}/admin/restaurant/{restaurant_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print(f"✅ DELETED: {result['message']}")
        if 'deleted' in result:
            print(f"   Cleaned up: {result['deleted']['embeddings']} embeddings, {result['deleted']['messages']} messages, {result['deleted']['clients']} clients")
    elif delete_response.status_code == 404:
        print(f"✅ Already deleted or doesn't exist")
    else:
        print(f"⚠️  Admin endpoint not ready ({delete_response.status_code}), trying owner endpoint...")
        
        # If admin endpoint fails, try logging in as the restaurant itself (if we knew the password)
        # For now, we'll just note it needs manual deletion
        print(f"   Manual deletion required for {restaurant_id}")

# Verify final state
print("\n📊 VERIFYING FINAL STATE")
print("=" * 60)

time.sleep(2)  # Give database time to update

list_response = requests.get(f"{BASE_URL}/restaurant/list")
if list_response.status_code == 200:
    restaurants = list_response.json()
    print(f"\nRemaining restaurants: {len(restaurants)}")
    for r in restaurants:
        print(f"✅ {r.get('name', 'Unknown')} ({r['restaurant_id']}) - {len(r.get('menu', []))} menu items")
    
    # Check if dummies are gone
    remaining_ids = [r['restaurant_id'] for r in restaurants]
    deleted_count = sum(1 for dummy in dummy_restaurants if dummy not in remaining_ids)
    
    if deleted_count > 0:
        print(f"\n🎉 Successfully deleted {deleted_count} dummy restaurants!")
    
    if any(dummy in remaining_ids for dummy in dummy_restaurants):
        still_there = [dummy for dummy in dummy_restaurants if dummy in remaining_ids]
        print(f"\n⚠️  Still need to delete: {', '.join(still_there)}")
        print("The admin endpoint might need more time to deploy.")

print("\n✅ Process complete!")