#!/usr/bin/env python3
"""
Sync embeddings via API for restaurants that need it
"""
import requests
import json

BASE_URL = "https://restaurantchat-production.up.railway.app"

def check_and_report():
    """Just check and report status without auth"""
    print("🔍 CHECKING EMBEDDING STATUS")
    print("=" * 60)
    
    # Get all restaurants (public endpoint)
    response = requests.get(f"{BASE_URL}/restaurant/list")
    if response.status_code != 200:
        print(f"❌ Failed to get restaurants: {response.status_code}")
        return
    
    restaurants = response.json()
    need_sync = []
    
    print(f"Found {len(restaurants)} restaurants\n")
    
    for restaurant in restaurants:
        restaurant_id = restaurant['restaurant_id']
        name = restaurant.get('name', restaurant_id)
        menu_count = len(restaurant.get('menu', []))
        
        # Get detailed info
        info_response = requests.get(f"{BASE_URL}/restaurant/info?restaurant_id={restaurant_id}")
        if info_response.status_code == 200:
            data = info_response.json()
            embedding_status = data.get('embedding_status', {})
            
            if embedding_status.get('sync_needed', False) and menu_count > 0:
                need_sync.append({
                    'id': restaurant_id,
                    'name': name,
                    'menu_count': menu_count,
                    'embedding_count': embedding_status.get('embedding_count', 0)
                })
                print(f"⚠️  {name} needs sync: {embedding_status.get('embedding_count', 0)}/{menu_count} embeddings")
            else:
                print(f"✅ {name}: {embedding_status.get('embedding_count', 0)}/{menu_count} embeddings")
    
    print("\n" + "=" * 60)
    print(f"📊 SUMMARY")
    print("=" * 60)
    print(f"Total restaurants: {len(restaurants)}")
    print(f"Need sync: {len(need_sync)}")
    
    if need_sync:
        print("\n⚠️  MANUAL SYNC NEEDED FOR:")
        for r in need_sync:
            print(f"- {r['name']} ({r['id']}): Has {r['embedding_count']}/{r['menu_count']} embeddings")
        
        print("\n💡 HOW TO FIX:")
        print("1. Restaurant owners should update their menu via the frontend admin panel")
        print("2. Any menu update will trigger embedding regeneration")
        print("3. Or use the admin API endpoints if you have admin access")
        
        # Show which restaurants specifically need attention
        print("\n🔧 PRIORITY RESTAURANTS:")
        priority = [r for r in need_sync if r['menu_count'] > 10]
        for r in sorted(priority, key=lambda x: x['menu_count'], reverse=True):
            print(f"   - {r['name']}: {r['menu_count']} menu items need embedding")

def suggest_curl_commands():
    """Suggest curl commands for manual sync"""
    print("\n📝 MANUAL SYNC COMMANDS")
    print("=" * 60)
    print("If you have admin access, you can use these commands:")
    print("\n1. First, get auth token:")
    print("""
curl -X POST https://restaurantchat-production.up.railway.app/restaurant/login \\
  -H "Content-Type: application/json" \\
  -d '{"restaurant_id":"admin@admin.com","password":"YOUR_PASSWORD"}'
""")
    
    print("\n2. Then sync all restaurants:")
    print("""
curl -X POST https://restaurantchat-production.up.railway.app/embeddings/admin/initialize-all \\
  -H "Authorization: Bearer YOUR_TOKEN"
""")
    
    print("\n3. Or sync specific restaurant:")
    print("""
curl -X POST https://restaurantchat-production.up.railway.app/embeddings/admin/initialize/RESTAURANT_ID \\
  -H "Authorization: Bearer YOUR_TOKEN"
""")

if __name__ == "__main__":
    check_and_report()
    suggest_curl_commands()