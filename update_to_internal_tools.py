#!/usr/bin/env python3
"""Update bella_vista to use internal_tools"""

import psycopg2

conn_string = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

try:
    print("🔧 Updating bella_vista to use internal_tools...")
    conn = psycopg2.connect(conn_string)
    cur = conn.cursor()
    
    # Update RAG mode
    cur.execute("""
        UPDATE restaurants 
        SET rag_mode = 'internal_tools'
        WHERE restaurant_id = 'bella_vista_restaurant'
    """)
    
    updated = cur.rowcount
    
    if updated > 0:
        conn.commit()
        print("✅ Successfully updated bella_vista_restaurant to use 'internal_tools'")
        
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
    
    print("\n✨ Ready to test internal tool flow!")
    print("   The system will now handle tools internally without intermediate messages.")
    
except Exception as e:
    print(f"❌ Error: {e}")