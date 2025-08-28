import sys
sys.path.append('.')

from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Check both tables
    print("Checking businesses table...")
    query = text("""
        SELECT business_id, rag_mode, business_type
        FROM businesses 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    
    result = db.execute(query).fetchone()
    if result:
        print(f"Found in businesses table:")
        print(f"  ID: {result.business_id}")
        print(f"  RAG Mode: {result.rag_mode}")
        print(f"  Type: {result.business_type}")
    
    print("\nChecking restaurants table...")
    query = text("""
        SELECT restaurant_id, rag_mode
        FROM restaurants 
        WHERE restaurant_id = 'bella_vista_restaurant'
    """)
    
    result = db.execute(query).fetchone()
    if result:
        print(f"Found in restaurants table:")
        print(f"  ID: {result.restaurant_id}")
        print(f"  RAG Mode: {result.rag_mode}")
        
    # Update to use full_menu mode
    print("\n\nTo fix the issue, run this SQL:")
    print("UPDATE businesses SET rag_mode = 'full_menu' WHERE business_id = 'bella_vista_restaurant';")
    print("UPDATE restaurants SET rag_mode = 'full_menu' WHERE restaurant_id = 'bella_vista_restaurant';")
    
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()