#!/usr/bin/env python3
"""Update restaurant to use internal_tools_v3"""
import psycopg2
import os
from urllib.parse import urlparse

# Parse DATABASE_URL
DATABASE_URL = 'postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway'
parsed = urlparse(DATABASE_URL)

# Connect
conn = psycopg2.connect(
    host=parsed.hostname,
    port=parsed.port,
    user=parsed.username,
    password=parsed.password,
    database=parsed.path[1:]
)

try:
    cursor = conn.cursor()
    
    # First check current mode
    cursor.execute("""
        SELECT rag_mode FROM businesses 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    current = cursor.fetchone()
    print(f"Current RAG mode: {current[0] if current else 'Not found'}")
    
    # Update to internal_tools_v3
    cursor.execute("""
        UPDATE businesses 
        SET rag_mode = 'internal_tools_v3'
        WHERE business_id = 'bella_vista_restaurant'
    """)
    
    conn.commit()
    print("✅ Updated to internal_tools_v3")
    
    # Verify
    cursor.execute("""
        SELECT business_id, name, rag_mode 
        FROM businesses 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    result = cursor.fetchone()
    print(f"Verified: {result}")
    
except Exception as e:
    print(f"Error: {e}")
    conn.rollback()
finally:
    conn.close()