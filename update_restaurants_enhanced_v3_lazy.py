#!/usr/bin/env python3
"""
Update all restaurants to use enhanced_v3_lazy RAG mode
This service has full memory features with Redis support
"""
import psycopg2
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')

if not DATABASE_URL:
    print("❌ DATABASE_URL not found in environment")
    exit(1)

try:
    # Connect to Railway PostgreSQL
    print("🔄 Connecting to Railway PostgreSQL...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    # Update all restaurants to use enhanced_v3_lazy
    print("🔄 Updating all restaurants to use enhanced_v3_lazy mode...")
    cur.execute("""
        UPDATE restaurants 
        SET rag_mode = 'enhanced_v3_lazy'
        WHERE rag_mode IS NOT NULL
        RETURNING restaurant_id
    """)
    
    updated_ids = cur.fetchall()
    update_count = len(updated_ids)
    
    # Commit the changes
    conn.commit()
    print(f"✅ Updated {update_count} restaurants to use enhanced_v3_lazy mode")
    
    # Verify the update
    print("\n🔍 Verifying update...")
    cur.execute("""
        SELECT rag_mode, COUNT(*) as count
        FROM restaurants
        GROUP BY rag_mode
        ORDER BY count DESC
    """)
    
    print("\nRAG mode distribution:")
    for row in cur.fetchall():
        mode = row[0] or 'NULL'
        count = row[1]
        print(f"  - {mode}: {count} restaurants")
    
    # Show sample restaurants
    print("\n📋 Sample restaurants with enhanced_v3_lazy:")
    cur.execute("""
        SELECT restaurant_id, data->>'name' as name, rag_mode
        FROM restaurants
        WHERE rag_mode = 'enhanced_v3_lazy'
        LIMIT 5
    """)
    
    for row in cur.fetchall():
        restaurant_id = row[0]
        name = row[1] or 'Unknown'
        rag_mode = row[2]
        print(f"  - {name} (ID: {restaurant_id}): {rag_mode}")
    
    # Close connection
    cur.close()
    conn.close()
    print("\n✅ Database update completed successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    if 'conn' in locals():
        conn.rollback()
        conn.close()