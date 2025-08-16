#!/usr/bin/env python3
"""Delete dummy restaurants with corrupted/test data"""
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
print("✅ Logged in successfully")

# Restaurants to delete (dummy/corrupted data)
restaurants_to_delete = [
    ("Test", "Dummy restaurant with placeholder menu"),
    ("Labrisa", "La Brisa - dummy menu item"),
    ("RestoLorenzo", "Lorenzo Papa - corrupted menu data")
]

print("\n🗑️  DELETING DUMMY RESTAURANTS")
print("=" * 60)

for restaurant_id, description in restaurants_to_delete:
    print(f"\n❌ Deleting {restaurant_id} ({description})...")
    
    # First, we need to login as that restaurant to delete it
    # Since we're admin, we can't directly delete other restaurants
    # Let's check if there's an admin delete endpoint
    
    # Try admin delete endpoint (if it exists)
    headers = {"Authorization": f"Bearer {token}"}
    
    # Check if restaurant exists first
    info_response = requests.get(f"{BASE_URL}/restaurant/info?restaurant_id={restaurant_id}")
    if info_response.status_code == 404:
        print(f"   Already deleted or doesn't exist")
        continue
    
    # Since there's no admin delete endpoint, we need to use SQL or have restaurant owners delete
    print(f"   ⚠️  Cannot delete via API - restaurant owner must delete their own account")
    print(f"   Alternative: Remove from database directly")

print("\n" + "=" * 60)
print("📋 MANUAL DELETION REQUIRED")
print("=" * 60)
print("\nSince the API requires restaurant owners to delete their own accounts,")
print("you'll need to either:")
print("\n1. Login as each restaurant and use DELETE /restaurant/delete")
print("2. Delete directly from the database:")
print("\n   -- Delete embeddings first")
print("   DELETE FROM menu_embeddings WHERE restaurant_id IN ('Test', 'Labrisa', 'RestoLorenzo');")
print("\n   -- Then delete restaurants")
print("   DELETE FROM restaurants WHERE restaurant_id IN ('Test', 'Labrisa', 'RestoLorenzo');")
print("\n3. Create an admin delete endpoint that bypasses owner check")

# Let's at least check the final status
print("\n📊 CURRENT STATUS:")
response = requests.get(f"{BASE_URL}/restaurant/list")
if response.status_code == 200:
    restaurants = response.json()
    print(f"\nTotal restaurants: {len(restaurants)}")
    for r in restaurants:
        menu_count = len(r.get('menu', []))
        if menu_count == 0 or (menu_count == 1 and r.get('menu', [{}])[0].get('title') == 'Unknown Dish'):
            print(f"❌ {r.get('name', 'Unknown')} ({r['restaurant_id']}) - Dummy/Empty")
        else:
            print(f"✅ {r.get('name', 'Unknown')} ({r['restaurant_id']}) - {menu_count} items")