"""
Check for lobster dishes in menu
"""
import psycopg2
import json

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def check_lobster_dish():
    conn = None
    cur = None
    try:
        # Connect to database
        print("Searching for lobster dishes...")
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
            
            # Search for lobster dishes
            if 'menu' in data and data['menu']:
                lobster_dishes = []
                for item in data['menu']:
                    dish_name = item.get('dish', '').lower()
                    if 'lobster' in dish_name:
                        lobster_dishes.append(item)
                
                if lobster_dishes:
                    print(f"\nFound {len(lobster_dishes)} lobster dish(es):")
                    print("="*50)
                    for dish in lobster_dishes:
                        print(f"\nDish: {dish.get('dish')}")
                        print(f"Category: {dish.get('subcategory')}")
                        print(f"Price: {dish.get('price')}")
                        print(f"Description: {dish.get('description')}")
                        print(f"Ingredients: {dish.get('ingredients')}")
                        print(f"Allergens: {dish.get('allergens')}")
                else:
                    print("\nNo lobster dishes found!")
                    # Let's check for ravioli
                    ravioli_dishes = []
                    for item in data['menu']:
                        dish_name = item.get('dish', '').lower()
                        if 'ravioli' in dish_name:
                            ravioli_dishes.append(item)
                    
                    if ravioli_dishes:
                        print(f"\nBut found {len(ravioli_dishes)} ravioli dish(es):")
                        print("="*50)
                        for dish in ravioli_dishes:
                            print(f"\nDish: {dish.get('dish')}")
                            print(f"Category: {dish.get('subcategory')}")
                            print(f"Price: {dish.get('price')}")
                            print(f"Description: {dish.get('description')}")
                            print(f"Ingredients: {dish.get('ingredients')}")
                            print(f"Allergens: {dish.get('allergens')}")
                
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
    check_lobster_dish()