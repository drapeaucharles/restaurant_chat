from sqlalchemy import create_engine, text
import json
import os

# Database URL
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://demo_user:securepassword@localhost:5432/restaurant_chat")

# Create engine
engine = create_engine(DATABASE_URL)

print("Checking for dishes with eggs...")

# Query to find items with eggs
query = text("""
    SELECT name, description, ingredients, allergens, category
    FROM menu_items 
    WHERE business_id = '1'
    AND (
        ingredients::text ILIKE '%egg%' 
        OR allergens::text ILIKE '%egg%'
        OR description ILIKE '%egg%'
    )
    ORDER BY name
""")

with engine.connect() as conn:
    results = conn.execute(query)
    
    dishes_with_eggs = []
    for row in results:
        # Parse ingredients if it's a JSON string
        ingredients = row.ingredients
        if isinstance(ingredients, str):
            try:
                ingredients = json.loads(ingredients)
            except:
                pass
        
        # Parse allergens if it's a JSON string  
        allergens = row.allergens
        if isinstance(allergens, str):
            try:
                allergens = json.loads(allergens)
            except:
                pass
                
        dishes_with_eggs.append({
            'name': row.name,
            'description': row.description,
            'ingredients': ingredients,
            'allergens': allergens,
            'category': row.category
        })
    
    print(f"\nFound {len(dishes_with_eggs)} dishes with eggs:\n")
    
    for dish in dishes_with_eggs:
        print(f"Name: {dish['name']}")
        print(f"Category: {dish['category']}")
        print(f"Description: {dish['description']}")
        print(f"Ingredients: {dish['ingredients']}")
        print(f"Allergens: {dish['allergens']}")
        print("-" * 50)

# Also check what the embedding search returns
print("\n\nNow checking what embedding search might return for 'eggs'...")
query2 = text("""
    SELECT name, description 
    FROM menu_items 
    WHERE business_id = '1'
    AND name IN ('Spaghetti Carbonara', 'Tiramisu', 'Chocolate Lava Cake', 'Crème Brûlée', 'Cheesecake')
""")

with engine.connect() as conn:
    results = conn.execute(query2)
    print("\nKnown egg dishes that should be found:")
    for row in results:
        print(f"- {row.name}: {row.description}")