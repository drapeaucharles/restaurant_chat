#!/usr/bin/env python3
"""Delete dummy restaurants using simple admin endpoints"""
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

# First list all restaurants
print("\n📋 Listing all restaurants...")
list_response = requests.get(f"{BASE_URL}/simple-admin/list-all", headers=headers)

if list_response.status_code == 200:
    restaurants = list_response.json()
    print(f"Found {len(restaurants)} restaurants:")
    for r in restaurants:
        print(f"  - {r['name']} ({r['restaurant_id']}) - {r['menu_count']} items")
else:
    print(f"❌ Failed to list: {list_response.status_code}")

# Delete dummy restaurants
print("\n🗑️  DELETING DUMMY RESTAURANTS")
print("=" * 60)

dummy_restaurants = ["Test", "RestoLorenzo"]

for restaurant_id in dummy_restaurants:
    print(f"\n🗑️  Deleting {restaurant_id}...")
    
    delete_response = requests.delete(
        f"{BASE_URL}/simple-admin/delete/{restaurant_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print(f"✅ SUCCESS: {result['message']}")
    else:
        print(f"❌ Failed ({delete_response.status_code}): {delete_response.text}")

# Verify final state
print("\n📊 VERIFYING FINAL STATE")
print("=" * 60)

time.sleep(2)

# List via public endpoint (excludes admin)
public_response = requests.get(f"{BASE_URL}/restaurant/list")
if public_response.status_code == 200:
    restaurants = public_response.json()
    print(f"\nPublic restaurant list: {len(restaurants)} restaurants")
    for r in restaurants:
        print(f"✅ {r.get('name', 'Unknown')} ({r['restaurant_id']}) - {len(r.get('menu', []))} items")

# Also check admin view
admin_response = requests.get(f"{BASE_URL}/simple-admin/list-all", headers=headers)
if admin_response.status_code == 200:
    all_restaurants = admin_response.json()
    print(f"\nAdmin view (includes admin account): {len(all_restaurants)} total")
    for r in all_restaurants:
        icon = "👤" if r['role'] == 'admin' else "✅"
        print(f"{icon} {r['name']} ({r['restaurant_id']}) - Role: {r['role']}")

print("\n✅ DELETION COMPLETE!")