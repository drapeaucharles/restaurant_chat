"""
Fix subcategories for better organization
"""
import psycopg2

DB_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

# Proper subcategory mappings
CATEGORY_MAPPINGS = {
    # Appetizers
    'Truffle Arancini': 'Appetizers',
    'Caprese Skewers': 'Appetizers',
    'Calamari Fritti': 'Appetizers',
    'Bruschetta Trio': 'Appetizers',
    'Stuffed Mushrooms': 'Appetizers',
    'Shrimp Cocktail': 'Appetizers',
    'Spinach Artichoke Dip': 'Appetizers',
    'Beef Carpaccio': 'Appetizers',
    'Mezze Platter': 'Appetizers',
    'Oysters Rockefeller': 'Appetizers',
    
    # Soups
    'French Onion Soup': 'Soups',
    'Lobster Bisque': 'Soups',
    'Minestrone Soup': 'Soups',
    'Tom Yum Soup': 'Soups',
    
    # Salads
    'Caesar Salad': 'Salads',
    'Greek Salad': 'Salads',
    'Roasted Beet Salad': 'Salads',
    'Quinoa Power Bowl': 'Salads',
    
    # Pasta
    'Spaghetti Carbonara': 'Pasta',
    'Lobster Ravioli': 'Pasta',
    'Penne Arrabbiata': 'Pasta',
    'Seafood Linguine': 'Pasta',
    'Gnocchi Gorgonzola': 'Pasta',
    'Lasagna Bolognese': 'Pasta',
    
    # Risotto
    'Mushroom Risotto': 'Risotto',
    'Saffron Risotto': 'Risotto',
    
    # Meat
    'Filet Mignon': 'Meat',
    'Rack of Lamb': 'Meat',
    'Osso Buco': 'Meat',
    'Duck Confit': 'Meat',
    'Beef Short Ribs': 'Meat',
    'Pork Tenderloin': 'Meat',
    'Veal Piccata': 'Meat',
    'Ribeye Steak': 'Meat',
    
    # Seafood
    'Grilled Salmon': 'Seafood',
    'Sea Bass': 'Seafood',
    'Lobster Thermidor': 'Seafood',
    'Seared Scallops': 'Seafood',
    'Tuna Steak': 'Seafood',
    'Mixed Seafood Grill': 'Seafood',
    
    # Vegetarian
    'Eggplant Parmigiana': 'Vegetarian',
    'Vegetable Curry': 'Vegetarian',
    'Stuffed Bell Peppers': 'Vegetarian',
    'Mushroom Wellington': 'Vegetarian',
    'Buddha Bowl': 'Vegetarian',
    
    # Desserts
    'Tiramisu': 'Desserts',
    'Chocolate Lava Cake': 'Desserts',
    'Crème Brûlée': 'Desserts',
    'New York Cheesecake': 'Desserts',
    'Gelato Trio': 'Desserts'
}

def update_categories(conn):
    """Update all item categories"""
    cursor = conn.cursor()
    
    updated = 0
    for item_name, category in CATEGORY_MAPPINGS.items():
        cursor.execute("""
            UPDATE menu_embeddings 
            SET item_category = %s 
            WHERE restaurant_id = 'bella_vista_restaurant' 
            AND item_name = %s
        """, (category, item_name))
        
        if cursor.rowcount > 0:
            updated += cursor.rowcount
            print(f"✓ Updated {item_name} → {category}")
    
    conn.commit()
    
    # Show updated category breakdown
    cursor.execute("""
        SELECT item_category, COUNT(*) 
        FROM menu_embeddings 
        WHERE restaurant_id = 'bella_vista_restaurant'
        GROUP BY item_category
        ORDER BY COUNT(*) DESC
    """)
    
    print(f"\n{'='*50}")
    print(f"Updated {updated} items")
    print(f"\nNew category breakdown:")
    
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} items")
    
    cursor.close()

if __name__ == "__main__":
    print("Fixing subcategories...")
    
    try:
        conn = psycopg2.connect(DB_URL)
        update_categories(conn)
        conn.close()
        print("\nDone! Categories are now properly organized.")
    except Exception as e:
        print(f"Error: {e}")