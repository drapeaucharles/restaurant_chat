#!/usr/bin/env python3
"""Update Bella Vista restaurant to use full_menu_with_tools"""

import psycopg2

# Connect to Restaurant Backend DB
conn_string = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

try:
    print("🔍 Updating Bella Vista RAG mode...")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    # Update RAG mode
    cur.execute("""
        UPDATE restaurants 
        SET rag_mode = 'full_menu_with_tools'
        WHERE restaurant_id = 'bella_vista_restaurant'
    """)
    
    updated = cur.rowcount
    
    if updated > 0:
        conn.commit()
        print("✅ Successfully updated bella_vista_restaurant to use 'full_menu_with_tools'")
        
        # Verify the update
        cur.execute("""
            SELECT restaurant_id, rag_mode 
            FROM restaurants 
            WHERE restaurant_id = 'bella_vista_restaurant'
        """)
        result = cur.fetchone()
        print(f"   Verified: {result[0]} now has rag_mode = '{result[1]}'")
    else:
        print("❌ No restaurant found with ID 'bella_vista_restaurant'")
    
    cur.close()
    conn.close()
    
    print("\n✨ Bella Vista is now configured for optimal tool-calling experience!")
    print("   Visit: https://restaurantfront-production.up.railway.app/chat?restaurant_id=bella_vista_restaurant&table_id=1")
    
except Exception as e:
    print(f"❌ Error: {e}")