#!/usr/bin/env python3
"""
Fix database allergen inconsistencies for bella_vista_restaurant
Run this script to correct the 3 identified issues
"""

import psycopg2
import json
import sys
from datetime import datetime

# Database connection - using environment variable or default
DB_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

def fix_allergen_inconsistencies():
    """Fix the specific allergen inconsistencies found in testing"""
    
    try:
        # Connect to database
        conn = psycopg2.connect(DB_URL)
        cur = conn.cursor()
        
        print(f"\n{'='*60}")
        print("DATABASE ALLERGEN FIX SCRIPT")
        print(f"Started at: {datetime.now()}")
        print(f"{'='*60}\n")
        
        # Get the restaurant data
        cur.execute("""
            SELECT data
            FROM restaurants 
            WHERE restaurant_id = 'bella_vista_restaurant'
        """)
        
        result = cur.fetchone()
        if not result or not result[0]:
            print("ERROR: Restaurant not found!")
            return
        
        data = result[0]
        menu_items = data.get('menu', [])
        
        print(f"Found {len(menu_items)} menu items\n")
        
        # Track changes
        changes_made = []
        
        # Fix 1: Gnocchi Gorgonzola - has nuts in allergens but is_nut_free = True
        print("1. Fixing Gnocchi Gorgonzola...")
        for item in menu_items:
            if 'gnocchi gorgonzola' in item.get('dish', '').lower():
                print(f"   Found: {item.get('dish')}")
                print(f"   Current is_nut_free: {item.get('is_nut_free')}")
                print(f"   Allergens: {item.get('allergens')}")
                
                if 'nuts' in [a.lower() for a in item.get('allergens', [])] and item.get('is_nut_free', False):
                    item['is_nut_free'] = False
                    changes_made.append("Gnocchi Gorgonzola: is_nut_free changed from True to False")
                    print("   ✓ Fixed: is_nut_free = False")
                break
        
        # Fix 2: Mezze Platter - is_nut_free = False but no nuts
        print("\n2. Fixing Mezze Platter...")
        for item in menu_items:
            if 'mezze platter' in item.get('dish', '').lower():
                print(f"   Found: {item.get('dish')}")
                print(f"   Current is_nut_free: {item.get('is_nut_free')}")
                print(f"   Allergens: {item.get('allergens')}")
                print(f"   Ingredients: {item.get('ingredients', [])}")
                
                # Check if truly has no nuts
                allergens_lower = [a.lower() for a in item.get('allergens', [])]
                ingredients_lower = ' '.join([str(i).lower() for i in item.get('ingredients', [])])
                
                has_nuts = any('nut' in a for a in allergens_lower) or 'nut' in ingredients_lower
                
                if not has_nuts and item.get('is_nut_free') == False:
                    item['is_nut_free'] = True
                    changes_made.append("Mezze Platter: is_nut_free changed from False to True")
                    print("   ✓ Fixed: is_nut_free = True")
                break
        
        # Fix 3: Buddha Bowl - is_nut_free = False but no nuts
        print("\n3. Fixing Buddha Bowl...")
        for item in menu_items:
            if 'buddha bowl' in item.get('dish', '').lower():
                print(f"   Found: {item.get('dish')}")
                print(f"   Current is_nut_free: {item.get('is_nut_free')}")
                print(f"   Allergens: {item.get('allergens')}")
                print(f"   Ingredients: {item.get('ingredients', [])}")
                
                # Check if truly has no nuts
                allergens_lower = [a.lower() for a in item.get('allergens', [])]
                ingredients_lower = ' '.join([str(i).lower() for i in item.get('ingredients', [])])
                
                has_nuts = any('nut' in a for a in allergens_lower) or 'nut' in ingredients_lower
                
                if not has_nuts and item.get('is_nut_free') == False:
                    item['is_nut_free'] = True
                    changes_made.append("Buddha Bowl: is_nut_free changed from False to True")
                    print("   ✓ Fixed: is_nut_free = True")
                break
        
        # Update database if changes were made
        if changes_made:
            print(f"\n{'='*40}")
            print("APPLYING CHANGES...")
            print(f"{'='*40}")
            
            # Update the restaurant data
            cur.execute("""
                UPDATE restaurants 
                SET data = %s
                WHERE restaurant_id = 'bella_vista_restaurant'
            """, [json.dumps(data)])
            
            conn.commit()
            
            print("\n✓ Database updated successfully!")
            print("\nChanges made:")
            for change in changes_made:
                print(f"  - {change}")
        else:
            print("\n✓ No changes needed - database already correct")
        
        # Close connection
        cur.close()
        conn.close()
        
        print(f"\n{'='*60}")
        print(f"Script completed at: {datetime.now()}")
        print(f"{'='*60}\n")
        
    except Exception as e:
        print(f"\nERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    fix_allergen_inconsistencies()