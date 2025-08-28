import sys
sys.path.append('.')

from database import SessionLocal
from sqlalchemy import text
import json
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL")

db = SessionLocal()

try:
    # First check columns
    query = text("""
        SELECT column_name 
        FROM information_schema.columns 
        WHERE table_name = 'businesses'
    """)
    
    result = db.execute(query)
    columns = [row[0] for row in result]
    print(f"Businesses table columns: {columns}\n")
    
    # Check businesses table
    query = text("""
        SELECT business_id, business_type, data
        FROM businesses
        WHERE business_type = 'restaurant'
        LIMIT 5
    """)
    
    result = db.execute(query)
    businesses = result.fetchall()
    
    print(f"Found {len(businesses)} restaurant businesses:\n")
    
    for biz in businesses:
        print(f"Business ID: {biz.business_id}")
        business_name = biz.data.get('name', biz.data.get('restaurant_name', 'Unknown')) if biz.data else 'No data'
        print(f"Name: {business_name}")
        print(f"RAG mode: {biz.rag_mode}")
        
        # Check if it has menu data
        if biz.data and 'menu' in biz.data:
            menu = biz.data['menu']
            print(f"Menu items: {len(menu)}")
            
            # Check for eggs
            eggs_count = 0
            for item in menu:
                name = item.get('name', '')
                desc = item.get('description', '')
                ing = item.get('ingredients', [])
                
                if 'egg' in name.lower() or 'egg' in desc.lower():
                    eggs_count += 1
                elif isinstance(ing, list) and any('egg' in str(i).lower() for i in ing):
                    eggs_count += 1
                    
            print(f"Items with eggs: {eggs_count}")
        else:
            print("No menu data found")
            
        print("-" * 50)
        
except Exception as e:
    print(f"Error: {e}")
finally:
    db.close()