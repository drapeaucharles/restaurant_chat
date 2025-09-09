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
    
    # Get all restaurants
    cur.execute("""
        SELECT restaurant_id, business_type, rag_mode, 
               jsonb_extract_path_text(data, 'business_name') as business_name,
               jsonb_array_length(data->'menu') as menu_count
        FROM restaurants 
        ORDER BY restaurant_id
    """)
    
    restaurants = cur.fetchall()
    
    print(f"\n📋 Found {len(restaurants)} restaurants:\n")
    print(f"{'ID':<30} {'Business Name':<30} {'Type':<15} {'RAG Mode':<20} {'Menu Items'}")
    print("-" * 110)
    
    for rest in restaurants:
        rest_id, biz_type, rag_mode, biz_name, menu_count = rest
        print(f"{rest_id:<30} {biz_name or 'N/A':<30} {biz_type or 'N/A':<15} {rag_mode or 'default':<20} {menu_count or 0}")
    
    # Check specifically for bella_vista
    print("\n🔍 Checking for 'bella_vista' variations...")
    cur.execute("""
        SELECT restaurant_id 
        FROM restaurants 
        WHERE restaurant_id LIKE '%bella%' OR restaurant_id LIKE '%vista%'
    """)
    bella_results = cur.fetchall()
    
    if bella_results:
        print(f"Found: {[r[0] for r in bella_results]}")
    else:
        print("No bella vista variations found")
    
    cur.close()
    conn.close()
    
    print("\n💡 To use the frontend, use one of the restaurant IDs above in the URL:")
    print("   https://restaurantfront-production.up.railway.app/chat?restaurant_id=RESTAURANT_ID&table_id=1")
    
except Exception as e:
    print(f"❌ Error: {e}")