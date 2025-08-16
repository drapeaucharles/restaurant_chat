#!/usr/bin/env python3
"""Final deletion using complete admin endpoint"""
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

# Delete dummy restaurants using force delete
print("\n🗑️  FORCE DELETING DUMMY RESTAURANTS")
print("=" * 60)

dummy_restaurants = ["Test", "RestoLorenzo"]

for restaurant_id in dummy_restaurants:
    print(f"\n🔥 Force deleting {restaurant_id}...")
    
    delete_response = requests.delete(
        f"{BASE_URL}/complete-admin/force-delete/{restaurant_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print(f"✅ SUCCESS: {result['message']}")
        if 'deleted' in result:
            deleted = result['deleted']
            print(f"   Deleted:")
            print(f"   - {deleted.get('embeddings', 0)} embeddings")
            print(f"   - {deleted.get('chat_logs', 0)} chat logs")
            print(f"   - {deleted.get('messages', 0)} messages")
            print(f"   - {deleted.get('clients', 0)} clients")
            print(f"   - {deleted.get('restaurant', 0)} restaurant record")
    else:
        print(f"❌ Failed ({delete_response.status_code}): {delete_response.text}")

# Final verification
print("\n📊 FINAL VERIFICATION")
print("=" * 60)

list_response = requests.get(f"{BASE_URL}/restaurant/list")
if list_response.status_code == 200:
    restaurants = list_response.json()
    print(f"\n✅ Remaining restaurants: {len(restaurants)}")
    for r in restaurants:
        print(f"   ✅ {r.get('name', 'Unknown')} ({r['restaurant_id']}) - {len(r.get('menu', []))} items")
    
    # Check if dummies are gone
    remaining_ids = [r['restaurant_id'] for r in restaurants]
    if not any(dummy in remaining_ids for dummy in dummy_restaurants):
        print("\n🎉 ALL DUMMY RESTAURANTS SUCCESSFULLY DELETED!")
    else:
        still_there = [d for d in dummy_restaurants if d in remaining_ids]
        print(f"\n⚠️  Still remaining: {still_there}")

print("\n✅ OPERATION COMPLETE!")