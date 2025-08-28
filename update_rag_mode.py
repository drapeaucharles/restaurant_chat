import sys
sys.path.append('.')

from database import SessionLocal
from sqlalchemy import text

db = SessionLocal()

try:
    # Update businesses table
    query = text("""
        UPDATE businesses 
        SET rag_mode = 'full_menu' 
        WHERE business_id = 'bella_vista_restaurant'
    """)
    
    result = db.execute(query)
    db.commit()
    print(f"Updated businesses table: {result.rowcount} rows")
    
    # Update restaurants table
    query = text("""
        UPDATE restaurants 
        SET rag_mode = 'full_menu' 
        WHERE restaurant_id = 'bella_vista_restaurant'
    """)
    
    result = db.execute(query)
    db.commit()
    print(f"Updated restaurants table: {result.rowcount} rows")
    
    print("\nBella Vista Restaurant is now using 'full_menu' mode!")
    print("This mode sends the complete menu, so 'I love eggs' will work properly.")
    
except Exception as e:
    print(f"Error: {e}")
    db.rollback()
finally:
    db.close()