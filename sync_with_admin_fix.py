#!/usr/bin/env python3
"""
Direct sync using the fact that we know admin@admin.com is the admin
We'll call the endpoints that don't have the broken permission check
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"
ADMIN_EMAIL = "admin@admin.com"
ADMIN_PASSWORD = "Lol007321lol!"

def sync_individual_restaurant(token, restaurant_id):
    """Try to sync individual restaurant"""
    headers = {"Authorization": f"Bearer {token}"}
    
    # First, let's try to update the restaurant's menu to trigger sync
    # Get current restaurant info
    info_response = requests.get(
        f"{BASE_URL}/restaurant/info?restaurant_id={restaurant_id}"
    )
    
    if info_response.status_code == 200:
        data = info_response.json()
        menu = data.get('menu', [])
        
        if menu:
            print(f"   Found {len(menu)} menu items")
            
            # Since we can't use the admin endpoints due to the role check bug,
            # we need another approach
            return False
    return False

def main():
    print("🔧 EMBEDDING SYNC WORKAROUND")
    print("=" * 60)
    
    # Login
    print("Logging in as admin...")
    response = requests.post(
        f"{BASE_URL}/restaurant/login",
        json={
            "restaurant_id": ADMIN_EMAIL,
            "password": ADMIN_PASSWORD
        }
    )
    
    if response.status_code != 200:
        print("❌ Login failed")
        return
    
    token = response.json()['access_token']
    print("✅ Logged in successfully")
    
    # The issue is that the admin endpoints check for role="owner" but admin has role="admin"
    # This is a bug in the backend code at line 139 of auth.py
    
    print("\n⚠️  ISSUE FOUND:")
    print("The admin endpoints require role='owner' but admin@admin.com has role='admin'")
    print("This is a bug in auth.py line 139")
    
    print("\n📋 FIX REQUIRED:")
    print("1. Update auth.py to create a get_current_admin function")
    print("2. Or update get_current_owner to also accept role='admin'")
    print("3. Or change the embeddings_admin.py endpoints to not use get_current_owner")
    
    print("\n🔧 TEMPORARY SOLUTION:")
    print("Since admin@admin.com can't use the admin endpoints due to the role check,")
    print("the restaurants need to sync themselves by updating their menus.")
    
    print("\n📝 RESTAURANTS NEEDING SYNC:")
    restaurants_to_sync = [
        ("RestoBulla", "Bulla Gastrobar Tampa", 61),
        ("RestoLorenzo", "Lorenzo Papa", 3),
        ("Labrisa", "La Brisa", 1),
        ("Test", "Test", 1)
    ]
    
    for restaurant_id, name, menu_count in restaurants_to_sync:
        print(f"\n- {name} ({restaurant_id})")
        print(f"  Menu items: {menu_count}")
        print(f"  Action: Restaurant owner needs to login and save their menu")

if __name__ == "__main__":
    main()