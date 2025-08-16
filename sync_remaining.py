#!/usr/bin/env python3
"""Sync remaining restaurants individually"""
import requests

BASE_URL = "https://restaurantchat-production.up.railway.app"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "Lol007321lol!"

# Login
print("Logging in...")
response = requests.post(
    f"{BASE_URL}/restaurant/login",
    json={"restaurant_id": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
)

if response.status_code != 200:
    print("Login failed")
    exit()

token = response.json()['access_token']
headers = {"Authorization": f"Bearer {token}"}

# Try to sync individual restaurants
restaurants_to_sync = ["Test", "Labrisa", "RestoLorenzo"]

for restaurant_id in restaurants_to_sync:
    print(f"\nSyncing {restaurant_id}...")
    
    response = requests.post(
        f"{BASE_URL}/embeddings/admin/rebuild/{restaurant_id}",
        headers=headers
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Success: {data}")
    else:
        print(f"❌ Failed ({response.status_code}): {response.text}")