#!/usr/bin/env python3
"""Use admin endpoints to delete dummy restaurants"""
import requests

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

# First get summary
print("\n📊 Getting restaurants summary...")
summary_response = requests.get(f"{BASE_URL}/admin/restaurants/summary", headers=headers)

if summary_response.status_code == 200:
    data = summary_response.json()
    print(f"\nTotal restaurants: {data['total_restaurants']}")
    
    # Identify dummy restaurants
    dummy_restaurants = []
    for r in data['restaurants']:
        if r['is_dummy'] or r['restaurant_id'] in ['Test', 'Labrisa', 'RestoLorenzo']:
            dummy_restaurants.append(r)
            print(f"❌ {r['name']} ({r['restaurant_id']}) - {r['menu_items']} items, {r['messages']} messages")
        else:
            print(f"✅ {r['name']} ({r['restaurant_id']}) - {r['menu_items']} items, {r['messages']} messages")
else:
    print(f"❌ Failed to get summary: {summary_response.status_code}")
    print(summary_response.text)
    exit()

# Delete dummy restaurants
print("\n🗑️  DELETING DUMMY RESTAURANTS")
print("=" * 60)

for r in dummy_restaurants:
    if r['restaurant_id'] == 'admin@admin.com':
        print(f"⏭️  Skipping admin account")
        continue
        
    print(f"\n❌ Deleting {r['name']} ({r['restaurant_id']})...")
    
    delete_response = requests.delete(
        f"{BASE_URL}/admin/restaurant/{r['restaurant_id']}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print(f"✅ {result['message']}")
        print(f"   Deleted: {result['deleted']['embeddings']} embeddings, {result['deleted']['messages']} messages, {result['deleted']['clients']} clients")
    else:
        print(f"❌ Failed: {delete_response.status_code}")
        print(delete_response.text)

# Final check
print("\n📊 FINAL STATUS")
print("=" * 60)

final_response = requests.get(f"{BASE_URL}/admin/restaurants/summary", headers=headers)
if final_response.status_code == 200:
    data = final_response.json()
    print(f"\nRemaining restaurants: {data['total_restaurants']}")
    for r in data['restaurants']:
        print(f"✅ {r['name']} ({r['restaurant_id']}) - {r['menu_items']} items")
        
print("\n✅ Cleanup complete!")