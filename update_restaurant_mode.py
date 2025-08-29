#!/usr/bin/env python3
"""
Update restaurant RAG mode to enable memory features
"""
import os
from sqlalchemy import create_engine, text

# Get database URL from environment
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    print("ERROR: DATABASE_URL not set")
    exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

# Restaurant to update
RESTAURANT_ID = 'bella_vista_restaurant'
NEW_RAG_MODE = 'memory_v6'  # or 'memory_universal'

with engine.connect() as conn:
    # Check current mode
    result = conn.execute(text("""
        SELECT restaurant_id, rag_mode 
        FROM restaurants 
        WHERE restaurant_id = :restaurant_id
    """), {"restaurant_id": RESTAURANT_ID})
    
    row = result.fetchone()
    if row:
        print(f"Current RAG mode for {RESTAURANT_ID}: {row.rag_mode}")
        
        # Update to memory-enabled mode
        conn.execute(text("""
            UPDATE restaurants 
            SET rag_mode = :new_mode 
            WHERE restaurant_id = :restaurant_id
        """), {"new_mode": NEW_RAG_MODE, "restaurant_id": RESTAURANT_ID})
        
        conn.commit()
        print(f"Updated RAG mode to: {NEW_RAG_MODE}")
        print("\nMemory features are now enabled!")
        print("The AI will remember:")
        print("- Customer names")
        print("- Conversation history")
        print("- Preferences and allergies")
    else:
        print(f"Restaurant {RESTAURANT_ID} not found")
        
    # Show all restaurants and their modes
    print("\nAll restaurants:")
    result = conn.execute(text("SELECT restaurant_id, rag_mode FROM restaurants ORDER BY restaurant_id"))
    for row in result:
        print(f"  {row.restaurant_id}: {row.rag_mode or 'default'}")