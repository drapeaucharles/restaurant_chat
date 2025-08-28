"""
Check menu item structure in database
"""
import psycopg2
import json
from pprint import pprint

DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def check_menu_structure():
    conn = None
    cur = None
    try:
        # Connect to database
        print("Connecting to database...")
        conn = psycopg2.connect(DATABASE_URL)
        cur = conn.cursor()
        
        # Get bella_vista_restaurant data
        print("\nFetching bella_vista_restaurant data...")
        cur.execute("""
            SELECT data 
            FROM businesses 
            WHERE business_id = 'bella_vista_restaurant'
        """)
        
        result = cur.fetchone()
        if result and result[0]:
            data = result[0]
            
            # Check menu items
            if 'menu' in data and data['menu']:
                print(f"\nFound {len(data['menu'])} menu items")
                
                # Analyze first few menu items to see all fields
                print("\nAnalyzing menu item structure:")
                print("="*50)
                
                # Get all unique keys across all menu items
                all_keys = set()
                for item in data['menu']:
                    all_keys.update(item.keys())
                
                print("\nAll unique fields found across menu items:")
                for key in sorted(all_keys):
                    print(f"  - {key}")
                
                # Show first 3 items as examples
                print("\n\nFirst 3 menu items (full structure):")
                print("="*50)
                for i, item in enumerate(data['menu'][:3]):
                    print(f"\nItem {i+1}:")
                    for key, value in sorted(item.items()):
                        if isinstance(value, list):
                            print(f"  {key}: {value}")
                        else:
                            print(f"  {key}: {repr(value)}")
                
                # Check for items with specific categories
                print("\n\nChecking category usage:")
                print("="*50)
                categories = {}
                subcategories = {}
                areas = {}
                restaurant_categories = {}
                
                for item in data['menu']:
                    cat = item.get('category', 'None')
                    subcat = item.get('subcategory', 'None')
                    area = item.get('area', 'None')
                    rest_cat = item.get('restaurant_category', 'None')
                    
                    categories[cat] = categories.get(cat, 0) + 1
                    subcategories[subcat] = subcategories.get(subcat, 0) + 1
                    areas[area] = areas.get(area, 0) + 1
                    restaurant_categories[rest_cat] = restaurant_categories.get(rest_cat, 0) + 1
                
                print("\nCategories used:")
                for cat, count in sorted(categories.items()):
                    print(f"  {cat}: {count} items")
                
                print("\nSubcategories used:")
                for subcat, count in sorted(subcategories.items()):
                    print(f"  {subcat}: {count} items")
                
                print("\nAreas used:")
                for area, count in sorted(areas.items()):
                    print(f"  {area}: {count} items")
                
                print("\nRestaurant Categories used:")
                for rest_cat, count in sorted(restaurant_categories.items()):
                    print(f"  {rest_cat}: {count} items")
                
            else:
                print("No menu items found")
                
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
    check_menu_structure()