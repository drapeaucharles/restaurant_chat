# pinecone_utils.py

import os
from dotenv import load_dotenv

from openai import OpenAI
from pinecone import Pinecone

# Load environment variables
load_dotenv()

# Load API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_INDEX = os.getenv("PINECONE_INDEX")

# Initialize OpenAI client (NEW SYNTAX)
client = OpenAI(api_key=OPENAI_API_KEY)

# Initialize Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)
index = pc.Index(PINECONE_INDEX)

# Create embedding with new OpenAI v1.x SDK
def create_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-ada-002",
        input=text
    )
    return response.data[0].embedding

# Insert restaurant data into Pinecone
def insert_restaurant_data(restaurant_id, content_dict):
    """
    Insert restaurant data into Pinecone with comprehensive context.
    Includes: name, story, menu, FAQ, opening hours
    """
    # Build formatted content for embedding
    content_parts = []
    
    # Restaurant Name
    name = content_dict.get("name", "")
    if name:
        content_parts.append(f"Restaurant Name: {name}")
    
    # Story
    story = content_dict.get("story", "")
    if story:
        content_parts.append(f"Story: {story}")
    
    # Opening Hours
    opening_hours = content_dict.get("opening_hours", "")
    if opening_hours:
        content_parts.append(f"Opening Hours: {opening_hours}")
    
    # Menu Section
    menu_items = content_dict.get("menu", [])
    if menu_items:
        content_parts.append("Menu:")
        for item in menu_items:
            # Handle both 'dish' and 'name' fields for flexibility
            dish_name = item.get("dish", "") or item.get("name", "")
            description = item.get("description", "")
            price = item.get("price", "")
            
            if dish_name:
                menu_line = f"- {dish_name}"
                if price:
                    menu_line += f" ({price})"
                if description:
                    menu_line += f": {description}"
                content_parts.append(menu_line)
    
    # FAQ Section
    faq_items = content_dict.get("faq", [])
    if faq_items:
        content_parts.append("FAQs:")
        for faq in faq_items:
            question = faq.get("question", "")
            answer = faq.get("answer", "")
            if question and answer:
                content_parts.append(f"- Q: {question} A: {answer}")
    
    # Join all parts with double newlines for clear separation
    content_text = "\n\n".join(content_parts)
    
    # Create embedding only if we have content
    if content_text.strip():
        embedding = create_embedding(content_text)
        
        index.upsert([
            (f"restaurant_{restaurant_id}", embedding)
        ])
    else:
        print(f"Warning: No content to embed for restaurant {restaurant_id}")

# Insert client preferences into Pinecone
def insert_client_preferences(client_id, preferences_dict):
    preferences_text = "\n".join([
        f"{key}: {value}" for key, value in preferences_dict.items()
    ])

    embedding = create_embedding(preferences_text)

    index.upsert([
        (f"client_{client_id}", embedding)
    ])

# Query Pinecone for combined search
def query_pinecone(restaurant_id, client_id, user_message):
    query_embedding = create_embedding(user_message)

    namespace_ids = [
        f"restaurant_{restaurant_id}",
        f"client_{client_id}"
    ]

    results = index.query(
        vector=query_embedding,
        top_k=3,
        include_metadata=False,
        filter={"id": {"$in": namespace_ids}}
    )

    return results

# Insert individual menu items into Pinecone for semantic search
def index_menu_items(restaurant_id, menu_items):
    """
    Index each menu item individually for more efficient semantic search.
    This allows us to retrieve only relevant items instead of the entire menu.
    """
    vectors_to_upsert = []
    
    for item in menu_items:
        # Get item name (handle both 'title' and 'dish' fields)
        item_name = item.get('title') or item.get('dish', '')
        if not item_name:
            continue
            
        # Build rich text representation for embedding
        text_parts = [f"Dish: {item_name}"]
        
        # Add category
        if item.get('category'):
            text_parts.append(f"Category: {item['category']}")
            
        # Add subcategory
        if item.get('subcategory'):
            text_parts.append(f"Subcategory: {item['subcategory']}")
            
        # Add description
        if item.get('description'):
            text_parts.append(f"Description: {item['description']}")
            
        # Add ingredients
        ingredients = item.get('ingredients', [])
        if ingredients:
            text_parts.append(f"Ingredients: {', '.join(ingredients)}")
            
        # Add allergens
        allergens = item.get('allergens', [])
        if allergens:
            text_parts.append(f"Allergens: {', '.join(allergens)}")
            
        # Add dietary tags
        if item.get('vegetarian'):
            text_parts.append("Vegetarian")
        if item.get('vegan'):
            text_parts.append("Vegan")
        if item.get('gluten_free'):
            text_parts.append("Gluten-free")
        if item.get('spicy'):
            text_parts.append("Spicy")
            
        # Create embedding text
        embedding_text = " | ".join(text_parts)
        
        # Create embedding
        embedding = create_embedding(embedding_text)
        
        # Create unique ID for this menu item
        item_id = f"menu_{restaurant_id}_{item_name.replace(' ', '_').lower()}"
        
        # Prepare metadata
        metadata = {
            "restaurant_id": restaurant_id,
            "item_name": item_name,
            "category": item.get('category', 'Uncategorized'),
            "subcategory": item.get('subcategory', ''),
            "description": item.get('description', ''),
            "ingredients": ingredients,
            "allergens": allergens,
            "price": item.get('price', ''),
            "type": "menu_item"
        }
        
        vectors_to_upsert.append({
            "id": item_id,
            "values": embedding,
            "metadata": metadata
        })
    
    # Batch upsert all menu items
    if vectors_to_upsert:
        index.upsert(vectors=vectors_to_upsert)
        print(f"Indexed {len(vectors_to_upsert)} menu items for restaurant {restaurant_id}")
    
    return len(vectors_to_upsert)

# Search for relevant menu items based on user query
def search_menu_items(restaurant_id, query, top_k=10):
    """
    Search for relevant menu items based on user query.
    Returns only the menu items that are semantically relevant to the query.
    """
    # Create embedding for the query
    query_embedding = create_embedding(query)
    
    # Search with metadata filter for this restaurant's menu items
    results = index.query(
        vector=query_embedding,
        top_k=top_k,
        include_metadata=True,
        filter={
            "restaurant_id": {"$eq": restaurant_id},
            "type": {"$eq": "menu_item"}
        }
    )
    
    # Extract menu items from results
    relevant_items = []
    for match in results.matches:
        if match.metadata:
            item = {
                "title": match.metadata.get("item_name", ""),
                "category": match.metadata.get("category", ""),
                "subcategory": match.metadata.get("subcategory", ""),
                "description": match.metadata.get("description", ""),
                "ingredients": match.metadata.get("ingredients", []),
                "allergens": match.metadata.get("allergens", []),
                "price": match.metadata.get("price", ""),
                "relevance_score": match.score
            }
            relevant_items.append(item)
    
    return relevant_items
