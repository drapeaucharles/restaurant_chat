#!/usr/bin/env python3
"""
Index menu items directly into the database
"""
import psycopg2
import json
import requests
import os
from datetime import datetime

# Database connection
DATABASE_URL = "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

# HuggingFace API for embeddings
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY", "")  # Get from environment
MODEL_ID = "BAAI/bge-small-en-v1.5"
API_URL = f"https://api-inference.huggingface.co/models/{MODEL_ID}"

if not HUGGINGFACE_API_KEY:
    print("❌ HUGGINGFACE_API_KEY not set in environment")
    print("   Set it with: export HUGGINGFACE_API_KEY=your-key-here")
    exit(1)

# Sample menu items for Bella Vista Restaurant
MENU_ITEMS = [
    {
        "id": "1",
        "dish": "Spaghetti Carbonara",
        "description": "Classic Roman pasta with guanciale, egg yolk, and pecorino romano",
        "price": "$18.99",
        "subcategory": "Pasta",
        "ingredients": ["spaghetti", "guanciale", "egg yolk", "pecorino romano", "black pepper"]
    },
    {
        "id": "2", 
        "dish": "Lobster Ravioli",
        "description": "Handmade ravioli filled with lobster in a light tomato cream sauce",
        "price": "$28.99",
        "subcategory": "Pasta",
        "ingredients": ["ravioli", "lobster", "tomato", "cream", "basil"]
    },
    {
        "id": "3",
        "dish": "Penne Arrabbiata",
        "description": "Penne pasta in a spicy tomato sauce with garlic and red chilies",
        "price": "$16.99",
        "subcategory": "Pasta",
        "ingredients": ["penne", "tomato", "garlic", "red chilies", "olive oil"],
        "vegetarian": True
    },
    {
        "id": "4",
        "dish": "Seafood Linguine",
        "description": "Linguine with shrimp, scallops, and mussels in a white wine sauce",
        "price": "$32.99",
        "subcategory": "Pasta",
        "ingredients": ["linguine", "shrimp", "scallops", "mussels", "white wine", "garlic"]
    },
    {
        "id": "5",
        "dish": "Gnocchi Gorgonzola",
        "description": "Potato gnocchi in a creamy gorgonzola sauce with walnuts",
        "price": "$19.99",
        "subcategory": "Pasta",
        "ingredients": ["gnocchi", "gorgonzola", "cream", "walnuts"],
        "vegetarian": True
    },
    {
        "id": "6",
        "dish": "Lasagna Bolognese",
        "description": "Traditional lasagna with meat sauce, bechamel, and mozzarella",
        "price": "$20.99",
        "subcategory": "Pasta",
        "ingredients": ["lasagna sheets", "ground beef", "tomato sauce", "bechamel", "mozzarella", "parmesan"]
    },
    {
        "id": "7",
        "dish": "Margherita Pizza",
        "description": "Fresh tomatoes, mozzarella, and basil on thin crust",
        "price": "$14.99",
        "subcategory": "Pizza",
        "ingredients": ["pizza dough", "tomato sauce", "mozzarella", "basil"],
        "vegetarian": True
    },
    {
        "id": "8",
        "dish": "Caesar Salad",
        "description": "Romaine lettuce, parmesan, croutons, and Caesar dressing",
        "price": "$12.99",
        "subcategory": "Salads",
        "ingredients": ["romaine lettuce", "parmesan", "croutons", "caesar dressing", "anchovies"]
    }
]

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
        return response.json()
    else:
        print(f"Error creating embedding: {response.status_code}")
        return None

def create_menu_item_text(item):
    """Create searchable text from menu item"""
    parts = []
    
    parts.append(f"Dish: {item['dish']}")
    parts.append(f"Description: {item['description']}")
    parts.append(f"Category: {item.get('subcategory', 'Main')}")
    parts.append(f"Ingredients: {', '.join(item.get('ingredients', []))}")
    parts.append(f"Price: {item['price']}")
    
    if item.get('vegetarian'):
        parts.append("Dietary: vegetarian")
    if item.get('vegan'):
        parts.append("Dietary: vegan")
    if item.get('gluten_free'):
        parts.append("Dietary: gluten-free")
    
    return " | ".join(parts)

def index_menu_items():
    """Index all menu items into the database"""
    print("🔧 Connecting to database...")
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    
    print("✅ Connected to database")
    
    # Clear existing data for bella_vista_restaurant
    print("\n📋 Clearing existing data...")
    cur.execute("DELETE FROM menu_embeddings WHERE restaurant_id = 'bella_vista_restaurant'")
    conn.commit()
    
    print(f"\n🍝 Indexing {len(MENU_ITEMS)} menu items...")
    
    indexed = 0
    for item in MENU_ITEMS:
        try:
            # Create full text
            full_text = create_menu_item_text(item)
            print(f"\n   Processing: {item['dish']}")
            
            # Create embedding
            embedding = create_embedding(full_text)
            if not embedding:
                print(f"   ❌ Failed to create embedding")
                continue
            
            # Prepare data
            dietary_tags = []
            if item.get('vegetarian'):
                dietary_tags.append('vegetarian')
            if item.get('vegan'):
                dietary_tags.append('vegan')
            if item.get('gluten_free'):
                dietary_tags.append('gluten-free')
            
            # Insert into database
            cur.execute("""
                INSERT INTO menu_embeddings 
                (restaurant_id, item_id, item_name, item_description, item_price, 
                 item_category, item_ingredients, dietary_tags, full_text, embedding_json)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            """, (
                'bella_vista_restaurant',
                item['id'],
                item['dish'],
                item['description'],
                item['price'],
                item.get('subcategory', 'Main'),
                json.dumps(item.get('ingredients', [])),
                json.dumps(dietary_tags),
                full_text,
                json.dumps(embedding)
            ))
            
            indexed += 1
            print(f"   ✅ Indexed successfully")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    conn.commit()
    
    # Verify
    cur.execute("SELECT COUNT(*) FROM menu_embeddings WHERE restaurant_id = 'bella_vista_restaurant'")
    count = cur.fetchone()[0]
    
    print(f"\n✅ Indexed {indexed} items successfully!")
    print(f"   Total items in database: {count}")
    
    cur.close()
    conn.close()
    
    return indexed

if __name__ == "__main__":
    print("🍝 Menu Indexing Script")
    print("=" * 50)
    
    indexed = index_menu_items()
    
    if indexed > 0:
        print("\n🎉 SUCCESS! Your RAG system is now fully operational!")
        print("\n📝 Test it with:")
        print('   curl -X POST https://restaurantchat-production.up.railway.app/chat \\')
        print('     -H "Content-Type: application/json" \\')
        print('     -d \'{"restaurant_id": "bella_vista_restaurant", "client_id": "550e8400-e29b-41d4-a716-446655440000", "sender_type": "client", "message": "What vegetarian pasta options do you have?"}\'')