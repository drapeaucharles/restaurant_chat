#!/usr/bin/env python3
"""Check what restaurants exist in the database"""

import psycopg2
import json

# Connect to Restaurant Backend DB
conn_string = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

try:
    print("🔍 Connecting to Restaurant Backend Database...")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    # First, check the structure
    cur.execute("""
        SELECT column_name, data_type 
        FROM information_schema.columns 
        WHERE table_name = 'restaurants'
        ORDER BY ordinal_position
    """)
    columns = cur.fetchall()
    print("\nTable structure:")
    for col in columns:
        print(f"  {col[0]}: {col[1]}")
    
    # Get all restaurants with simpler query
    cur.execute("""
        SELECT restaurant_id, business_type, rag_mode, data
        FROM restaurants 
        ORDER BY restaurant_id
        LIMIT 20
    """)
    
    restaurants = cur.fetchall()
    
    print(f"\n📋 Found {len(restaurants)} restaurants (showing first 20):\n")
    print(f"{'ID':<35} {'Business Name':<30} {'Type':<15} {'RAG Mode':<25}")
    print("-" * 105)
    
    for rest in restaurants:
        rest_id, biz_type, rag_mode, data = rest
        biz_name = "N/A"
        menu_count = 0
        
        # Parse data field
        if data:
            try:
                if isinstance(data, str):
                    data_dict = json.loads(data)
                else:
                    data_dict = data
                biz_name = data_dict.get('business_name', 'N/A')
                menu_items = data_dict.get('menu', [])
                menu_count = len(menu_items)
            except:
                pass
        
        print(f"{rest_id:<35} {biz_name:<30} {biz_type or 'restaurant':<15} {rag_mode or 'default':<25} [{menu_count} items]")
    
    # Check specifically for bella_vista
    print("\n🔍 Checking for 'bella_vista' variations...")
    cur.execute("""
        SELECT restaurant_id 
        FROM restaurants 
        WHERE restaurant_id LIKE '%bella%' OR restaurant_id LIKE '%vista%'
    """)
    bella_results = cur.fetchall()
    
    if bella_results:
        print(f"Found bella vista variations:")
        for r in bella_results:
            print(f"  - {r[0]}")
    else:
        print("No bella vista variations found")
    
    # Get total count
    cur.execute("SELECT COUNT(*) FROM restaurants")
    total_count = cur.fetchone()[0]
    print(f"\n📊 Total restaurants in database: {total_count}")
    
    cur.close()
    conn.close()
    
    print("\n💡 To use the frontend, use one of the restaurant IDs above in the URL:")
    print("   https://restaurantfront-production.up.railway.app/chat?restaurant_id=RESTAURANT_ID&table_id=1")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()