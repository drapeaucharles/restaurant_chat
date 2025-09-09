#!/bin/bash

# Update bella_vista_restaurant to use internal_tools_v4
python3 - << 'EOF'
import psycopg2
from urllib.parse import urlparse

DATABASE_URL = 'postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway'
parsed = urlparse(DATABASE_URL)

print("Updating bella_vista_restaurant to internal_tools_v4...")

try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:]
    )
    cursor = conn.cursor()
    
    # Update to V4
    cursor.execute("""
        UPDATE businesses 
        SET rag_mode = 'internal_tools_v4'
        WHERE business_id = 'bella_vista_restaurant'
    """)
    
    conn.commit()
    
    # Verify
    cursor.execute("""
        SELECT business_id, rag_mode 
        FROM businesses 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    result = cursor.fetchone()
    
    if result and result[1] == 'internal_tools_v4':
        print(f"✅ Updated successfully! New rag_mode: {result[1]}")
    else:
        print(f"❌ Update failed. Current value: {result[1] if result else 'Not found'}")
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Error: {e}")
EOF