#!/usr/bin/env python3
"""
Fix admin visibility and delete dummy restaurants
1. Update restaurant list endpoints to exclude admin
2. Delete dummy restaurants
"""
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

# Try to delete dummy restaurants using the admin endpoint
dummy_restaurants = ["Test", "Labrisa", "RestoLorenzo"]

print("\n🗑️  Attempting to delete dummy restaurants...")
for restaurant_id in dummy_restaurants:
    print(f"\nDeleting {restaurant_id}...")
    
    delete_response = requests.delete(
        f"{BASE_URL}/admin/restaurant/{restaurant_id}",
        headers=headers
    )
    
    if delete_response.status_code == 200:
        result = delete_response.json()
        print(f"✅ {result['message']}")
    elif delete_response.status_code == 500:
        print(f"❌ Server error - endpoint might not be deployed yet")
    else:
        print(f"❌ Failed: {delete_response.status_code}")
        print(delete_response.text)