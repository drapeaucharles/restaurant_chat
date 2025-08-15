"""
Direct database indexing of all 50 menu items
"""
import psycopg2
import json
import requests
import os
from datetime import datetime

# Database connection
DB_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

# HuggingFace API for embeddings
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
MODEL_ID = "BAAI/bge-small-en-v1.5"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

def create_embedding(text):
    """Create embedding using HuggingFace API"""
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    response = requests.post(
        API_URL,
        headers=headers,
        json={"inputs": text, "options": {"wait_for_model": True}},
        timeout=30
    )
    
    if response.status_code == 200:
        embedding = response.json()
        if isinstance(embedding, list) and len(embedding) > 0:
            if isinstance(embedding[0], list):
                return embedding[0]
            return embedding
    return None

def get_restaurant_menu(conn):
    """Get full menu from restaurant data"""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT data::text 
        FROM restaurants 
        WHERE restaurant_id = 'bella_vista_restaurant'
    """)
    
    result = cursor.fetchone()
    if result:
        data = json.loads(result[0])
        return data.get('menu', [])
    return []

def create_menu_item_text(item):
    """Create searchable text from menu item"""
    parts = []
    
    # Determine subcategory based on item
    name = item.get('dish', '')
    subcategory = item.get('subcategory', '')
    
    # Auto-detect subcategory if not provided
    if not subcategory:
        name_lower = name.lower()
        if any(pasta in name_lower for pasta in ['spaghetti', 'penne', 'linguine', 'ravioli', 'lasagna', 'gnocchi']):
            subcategory = 'Pasta'
        elif 'risotto' in name_lower:
            subcategory = 'Risotto'
        elif 'pizza' in name_lower:
            subcategory = 'Pizza'
        elif 'salad' in name_lower:
            subcategory = 'Salads'
        elif any(soup in name_lower for soup in ['soup', 'bisque']):
            subcategory = 'Soups'
        elif any(meat in name_lower for meat in ['filet', 'ribeye', 'steak', 'lamb', 'beef', 'pork', 'veal', 'duck']):
            subcategory = 'Meat'
        elif any(seafood in name_lower for seafood in ['salmon', 'sea bass', 'lobster', 'scallops', 'tuna', 'shrimp', 'oyster']):
            subcategory = 'Seafood'
        elif any(app in name_lower for app in ['arancini', 'bruschetta', 'calamari', 'carpaccio']):
            subcategory = 'Appetizers'
        elif any(dessert in name_lower for dessert in ['tiramisu', 'cake', 'cheesecake', 'gelato', 'crème']):
            subcategory = 'Desserts'
        else:
            # Default based on price range
            price = item.get('price', '').replace('$', '')
            try:
                price_num = float(price)
                if price_num < 15:
                    subcategory = 'Appetizers'
                elif price_num > 30:
                    subcategory = 'Main Courses'
                else:
                    subcategory = 'Entrées'
            except:
                subcategory = 'Specialties'
    
    parts.append(f"Dish: {name}")
    parts.append(f"Category: {subcategory}")
    
    # Add description
    desc = item.get('description', '')
    if desc:
        parts.append(f"Description: {desc}")
    
    # Add ingredients
    ingredients = item.get('ingredients', [])
    if ingredients and isinstance(ingredients, list):
        ing_list = [i for i in ingredients if i]  # Filter empty strings
        if ing_list:
            parts.append(f"Ingredients: {', '.join(ing_list)}")
    
    # Add price
    price = item.get('price', '')
    if price:
        parts.append(f"Price: {price}")
    
    # Add dietary info
    dietary = []
    # Auto-detect dietary info from name and ingredients
    full_text = f"{name} {desc} {' '.join(ingredients if isinstance(ingredients, list) else [])}".lower()
    
    if item.get('vegetarian') or not any(meat in full_text for meat in ['meat', 'beef', 'chicken', 'pork', 'lamb', 'duck', 'veal', 'bacon', 'prosciutto', 'guanciale', 'seafood', 'fish', 'shrimp', 'lobster']):
        if 'pasta' in full_text or 'pizza' in full_text or 'salad' in full_text:
            dietary.append('vegetarian')
    
    if item.get('vegan') or ('vegan' in full_text and not any(animal in full_text for animal in ['cheese', 'cream', 'butter', 'egg', 'milk'])):
        dietary.append('vegan')
    
    if item.get('gluten_free') or 'gluten-free' in full_text or 'gluten free' in full_text:
        dietary.append('gluten-free')
        
    if 'spicy' in full_text or 'arrabbiata' in full_text or 'chili' in full_text:
        dietary.append('spicy')
        
    if dietary:
        parts.append(f"Dietary: {', '.join(dietary)}")
    
    return " | ".join(parts), subcategory, dietary

def index_all_items(conn):
    """Index all menu items with embeddings"""
    cursor = conn.cursor()
    
    # Get menu
    menu_items = get_restaurant_menu(conn)
    print(f"Found {len(menu_items)} menu items")
    
    # Clear existing embeddings for this restaurant
    cursor.execute("""
        DELETE FROM menu_embeddings 
        WHERE restaurant_id = 'bella_vista_restaurant'
    """)
    conn.commit()
    print("Cleared existing embeddings")
    
    indexed = 0
    failed = 0
    
    for i, item in enumerate(menu_items):
        try:
            # Skip empty items
            if not item.get('dish'):
                continue
            
            # Create searchable text and metadata
            full_text, subcategory, dietary_tags = create_menu_item_text(item)
            
            # Create embedding
            print(f"\n[{i+1}/{len(menu_items)}] Creating embedding for: {item['dish']}")
            embedding = create_embedding(full_text)
            
            if not embedding:
                print(f"  ❌ Failed to create embedding")
                failed += 1
                continue
            
            # Prepare data for insertion
            item_data = {
                'restaurant_id': 'bella_vista_restaurant',
                'item_id': str(hash(item['dish'])),
                'item_name': item['dish'],
                'item_description': item.get('description', ''),
                'item_price': item.get('price', ''),
                'item_category': subcategory,
                'item_ingredients': ', '.join(item.get('ingredients', [])) if isinstance(item.get('ingredients'), list) else '',
                'dietary_tags': ', '.join(dietary_tags),
                'full_text': full_text,
                'embedding_json': json.dumps(embedding)
            }
            
            # Insert into database
            cursor.execute("""
                INSERT INTO menu_embeddings 
                (restaurant_id, item_id, item_name, item_description, item_price, 
                 item_category, item_ingredients, dietary_tags, full_text, embedding_json)
                VALUES 
                (%(restaurant_id)s, %(item_id)s, %(item_name)s, %(item_description)s, %(item_price)s,
                 %(item_category)s, %(item_ingredients)s, %(dietary_tags)s, %(full_text)s, %(embedding_json)s)
                ON CONFLICT (restaurant_id, item_id) 
                DO UPDATE SET
                    item_name = EXCLUDED.item_name,
                    item_description = EXCLUDED.item_description,
                    item_price = EXCLUDED.item_price,
                    item_category = EXCLUDED.item_category,
                    item_ingredients = EXCLUDED.item_ingredients,
                    dietary_tags = EXCLUDED.dietary_tags,
                    full_text = EXCLUDED.full_text,
                    embedding_json = EXCLUDED.embedding_json,
                    updated_at = CURRENT_TIMESTAMP
            """, item_data)
            
            indexed += 1
            print(f"  ✓ Indexed: {item['dish']} | Category: {subcategory} | Tags: {dietary_tags}")
            
        except Exception as e:
            print(f"  ❌ Error indexing {item.get('dish', 'Unknown')}: {e}")
            failed += 1
            conn.rollback()
            continue
    
    conn.commit()
    
    # Verify results
    cursor.execute("""
        SELECT item_category, COUNT(*) 
        FROM menu_embeddings 
        WHERE restaurant_id = 'bella_vista_restaurant'
        GROUP BY item_category
        ORDER BY COUNT(*) DESC
    """)
    
    print(f"\n{'='*60}")
    print(f"Indexing Complete!")
    print(f"Successfully indexed: {indexed} items")
    print(f"Failed: {failed} items")
    print(f"\nCategory breakdown:")
    
    for row in cursor.fetchall():
        print(f"  {row[0]}: {row[1]} items")
    
    cursor.close()

if __name__ == "__main__":
    print("Starting full menu indexing...")
    print(f"Time: {datetime.now()}")
    
    try:
        # Connect to database
        conn = psycopg2.connect(DB_URL)
        
        # Index all items
        index_all_items(conn)
        
        # Close connection
        conn.close()
        
        print("\nDone! All menu items are now indexed with embeddings.")
        
    except Exception as e:
        print(f"Error: {e}")