#!/usr/bin/env python3
"""Check admin account role"""
import requests

BASE_URL = "https://restaurantchat-production.up.railway.app"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "Lol007321lol!"

# Login
print("Logging in...")
response = requests.post(
    f"{BASE_URL}/restaurant/login",
    json={
        "restaurant_id": ADMIN_EMAIL,
        "password": ADMIN_PASSWORD
    }
)

if response.status_code == 200:
    data = response.json()
    print(f"✅ Login successful")
    print(f"Access token: {data.get('access_token', '')[:20]}...")
    
    # Check profile to see role
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    profile_response = requests.get(
        f"{BASE_URL}/restaurant/profile",
        headers=headers
    )
    
    if profile_response.status_code == 200:
        profile = profile_response.json()
        print(f"\nProfile info:")
        print(f"Restaurant ID: {profile.get('restaurant_id')}")
        print(f"Name: {profile.get('name')}")
        
    # Try to decode the JWT to see the role
    import base64
    import json
    
    token = data['access_token']
    # JWT has 3 parts separated by dots
    parts = token.split('.')
    if len(parts) >= 2:
        # Decode the payload (second part)
        # Add padding if needed
        payload = parts[1]
        payload += '=' * (4 - len(payload) % 4)
        
        decoded = base64.urlsafe_b64decode(payload)
        payload_data = json.loads(decoded)
        
        print(f"\nToken payload:")
        print(f"Subject: {payload_data.get('sub')}")
        print(f"Role: {payload_data.get('role')}")
        print(f"Type: {payload_data.get('type')}")
else:
    print(f"❌ Login failed: {response.status_code}")
    print(response.text)