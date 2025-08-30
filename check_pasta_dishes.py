#!/usr/bin/env python3
"""
Check for pasta dishes in menu
"""
import psycopg2
import json

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def check_pasta_dishes():
    conn = None
    cur = None
    try:
        # Connect to database
        print("Searching for pasta dishes...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get bella_vista_restaurant data
        cur.execute("""
            SELECT data 
            FROM businesses 
            WHERE business_id = 'bella_vista_restaurant'
        """)
        
        result = cur.fetchone()
        if result and result[0]:
            data = result[0]
            menu_items = data.get('menu', [])
            
            # Search for pasta dishes
            pasta_dishes = []
            for item in menu_items:
                # Check dish name
                dish_name = item.get('dish', '').lower()
                if 'pasta' in dish_name:
                    pasta_dishes.append((item, "in name"))
                    continue
                
                # Check ingredients
                ingredients = item.get('ingredients', [])
                if any('pasta' in ing.lower() for ing in ingredients):
                    pasta_dishes.append((item, "in ingredients"))
                    continue
                
                # Check description
                description = item.get('description', '').lower()
                if 'pasta' in description:
                    pasta_dishes.append((item, "in description"))
                    continue
                
                # Also check for specific pasta types
                pasta_types = ['spaghetti', 'ravioli', 'fettuccine', 'linguine', 'penne', 'rigatoni', 'lasagna', 'tagliatelle']
                if any(ptype in dish_name for ptype in pasta_types):
                    pasta_dishes.append((item, "pasta type in name"))
                elif any(ptype in description for ptype in pasta_types):
                    pasta_dishes.append((item, "pasta type in description"))
            
            print(f"\nFound {len(pasta_dishes)} pasta dish(es):")
            print("="*50)
            for dish, location in pasta_dishes:
                print(f"\nDish: {dish.get('dish')}")
                print(f"Category: {dish.get('subcategory')}")
                print(f"Price: {dish.get('price')}")
                print(f"Description: {dish.get('description')}")
                print(f"Found: {location}")
                
        else:
            print("Restaurant not found")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()

if __name__ == "__main__":
    check_pasta_dishes()