#!/usr/bin/env python3
"""
Monitor embedding sync status for all restaurants
Checks if embeddings are in sync with menu items
"""
import requests
import json
from datetime import datetime

BASE_URL = "https://restaurantchat-production.up.railway.app"

def check_all_restaurants():
    """Check embedding status for all restaurants"""
    print("🔍 EMBEDDING SYNC STATUS CHECK")
    print("=" * 80)
    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)
    
    # Get all restaurants
    try:
        response = requests.get(f"{BASE_URL}/restaurant/list")
        if response.status_code != 200:
            print(f"❌ Failed to get restaurant list: {response.status_code}")
            return
        
        restaurants = response.json()
        print(f"Found {len(restaurants)} restaurants\n")
        
        # Stats
        total_restaurants = len(restaurants)
        synced_restaurants = 0
        total_menu_items = 0
        total_embeddings = 0
        need_sync = []
        
        # Check each restaurant
        for restaurant in restaurants:
            restaurant_id = restaurant['restaurant_id']
            restaurant_name = restaurant.get('name', restaurant_id)
            
            # Get detailed info with embedding status
            detail_response = requests.get(f"{BASE_URL}/restaurant/info?restaurant_id={restaurant_id}")
            if detail_response.status_code == 200:
                data = detail_response.json()
                embedding_status = data.get('embedding_status', {})
                
                menu_count = embedding_status.get('menu_count', 0)
                embedding_count = embedding_status.get('embedding_count', 0)
                indexed = embedding_status.get('indexed', False)
                sync_needed = embedding_status.get('sync_needed', False)
                
                total_menu_items += menu_count
                total_embeddings += embedding_count
                
                # Display status
                if sync_needed or not indexed:
                    status_icon = "⚠️"
                    need_sync.append({
                        'id': restaurant_id,
                        'name': restaurant_name,
                        'menu_count': menu_count,
                        'embedding_count': embedding_count
                    })
                else:
                    status_icon = "✅"
                    synced_restaurants += 1
                
                print(f"{status_icon} {restaurant_name} ({restaurant_id})")
                print(f"   Menu items: {menu_count}")
                print(f"   Embeddings: {embedding_count}")
                print(f"   Status: {'IN SYNC' if not sync_needed else 'NEEDS SYNC'}")
                print()
            else:
                print(f"❌ Failed to get details for {restaurant_id}")
                print()
        
        # Summary
        print("=" * 80)
        print("📊 SUMMARY")
        print("=" * 80)
        print(f"Total restaurants: {total_restaurants}")
        print(f"Synced restaurants: {synced_restaurants} ({synced_restaurants/total_restaurants*100:.1f}%)")
        print(f"Need sync: {len(need_sync)}")
        print(f"Total menu items: {total_menu_items}")
        print(f"Total embeddings: {total_embeddings}")
        
        if need_sync:
            print("\n⚠️  RESTAURANTS NEEDING SYNC:")
            for r in need_sync:
                print(f"- {r['name']} ({r['id']}): {r['menu_count']} items, {r['embedding_count']} embeddings")
            
            print("\n💡 To fix sync issues:")
            print("1. Restaurant owners can update their menu via the admin panel")
            print("2. Or use the /admin/embeddings/sync endpoint")
        else:
            print("\n✅ All restaurants are properly synced!")
            
    except Exception as e:
        print(f"❌ Error: {e}")

def test_new_restaurant_flow():
    """Test if new restaurant registration creates embeddings"""
    print("\n\n🧪 TESTING NEW RESTAURANT REGISTRATION")
    print("=" * 80)
    
    # This would need actual test data and auth
    print("To test new restaurant registration:")
    print("1. Register a new restaurant via POST /register")
    print("2. Check if embeddings are created automatically")
    print("3. Update menu via PUT /restaurant/profile")
    print("4. Check if embeddings are updated")
    print("\n(This requires authentication, so showing the flow only)")

if __name__ == "__main__":
    check_all_restaurants()
    test_new_restaurant_flow()