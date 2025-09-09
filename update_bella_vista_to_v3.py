#!/usr/bin/env python3
"""Update bella_vista_restaurant to use internal_tools_v3"""
import psycopg2
from urllib.parse import urlparse

# Parse DATABASE_URL from .env
DATABASE_URL = 'postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway'
parsed = urlparse(DATABASE_URL)

print("🔄 Updating bella_vista_restaurant to internal_tools_v3\n")

try:
    # Connect to database
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port,
        user=parsed.username,
        password=parsed.password,
        database=parsed.path[1:]
    )
    cursor = conn.cursor()
    
    # Check current rag_mode
    print("1. Checking current rag_mode...")
    cursor.execute("""
        SELECT business_id, name, type, rag_mode 
        FROM businesses 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    result = cursor.fetchone()
    
    if result:
        print(f"   Found: {result[1]} (type: {result[2]})")
        print(f"   Current rag_mode: {result[3]}")
    else:
        print("   ❌ bella_vista_restaurant not found!")
        exit(1)
    
    # Update to internal_tools_v3
    print("\n2. Updating rag_mode to internal_tools_v3...")
    cursor.execute("""
        UPDATE businesses 
        SET rag_mode = 'internal_tools_v3'
        WHERE business_id = 'bella_vista_restaurant'
    """)
    
    # Commit the change
    conn.commit()
    print("   ✅ Update committed")
    
    # Verify the update
    print("\n3. Verifying update...")
    cursor.execute("""
        SELECT business_id, name, rag_mode 
        FROM businesses 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    result = cursor.fetchone()
    
    if result and result[2] == 'internal_tools_v3':
        print(f"   ✅ Success! {result[1]} now uses: {result[2]}")
    else:
        print(f"   ❌ Update may have failed. Current value: {result[2] if result else 'Not found'}")
    
    cursor.close()
    conn.close()
    
    print("\n✅ Database updated successfully!")
    print("bella_vista_restaurant is now set to use internal_tools_v3")
    
except Exception as e:
    print(f"❌ Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()