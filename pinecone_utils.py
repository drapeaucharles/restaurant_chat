# pinecone_utils.py

import os
from datetime import datetime, timedelta
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

# Search for relevant FAQ items based on user query
def search_relevant_faqs(restaurant_id, query, faqs, top_k=3):
    """
    Find the most relevant FAQ items based on semantic similarity to the query.
    This avoids sending all FAQs and reduces token usage.
    
    Args:
        restaurant_id: Restaurant identifier
        query: User's question
        faqs: List of FAQ dictionaries
        top_k: Number of FAQs to return
        
    Returns:
        List of most relevant FAQ items
    """
    if not faqs:
        return []
    
    # Create embeddings for all FAQs
    faq_embeddings = []
    valid_faqs = []
    
    for faq in faqs:
        question = faq.get('question', '')
        answer = faq.get('answer', '')
        if question and answer:
            # Combine question and answer for richer embedding
            faq_text = f"Q: {question} A: {answer}"
            try:
                embedding = create_embedding(faq_text)
                faq_embeddings.append(embedding)
                valid_faqs.append(faq)
            except Exception as e:
                print(f"Error creating embedding for FAQ: {e}")
                continue
    
    if not faq_embeddings:
        return []
    
    # Create embedding for the query
    query_embedding = create_embedding(query)
    
    # Calculate cosine similarity between query and each FAQ
    import numpy as np
    
    similarities = []
    for faq_emb in faq_embeddings:
        # Cosine similarity
        similarity = np.dot(query_embedding, faq_emb) / (np.linalg.norm(query_embedding) * np.linalg.norm(faq_emb))
        similarities.append(similarity)
    
    # Get indices of top-k most similar FAQs
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    # Return only FAQs with similarity above threshold (0.7)
    relevant_faqs = []
    for idx in top_indices:
        if similarities[idx] > 0.7:  # Relevance threshold
            relevant_faqs.append(valid_faqs[idx])
    
    return relevant_faqs

# Cache restaurant context in Pinecone for faster retrieval
def cache_restaurant_context(restaurant_id, context_data):
    """
    Cache the restaurant's context (name, basic info) in Pinecone.
    This reduces the need to rebuild context for every request.
    
    Args:
        restaurant_id: Restaurant identifier
        context_data: Dictionary with restaurant context
    """
    import hashlib
    
    # Create a unique ID for the context
    context_id = f"context_{restaurant_id}_{hashlib.md5(str(context_data).encode()).hexdigest()[:8]}"
    
    # Create text representation of context
    context_text = f"""
    Restaurant: {context_data.get('name', 'Unknown')}
    Type: Restaurant Context Cache
    Categories: {', '.join(context_data.get('categories', []))}
    Total Items: {context_data.get('item_count', 0)}
    Has FAQ: {'Yes' if context_data.get('has_faq') else 'No'}
    """
    
    # Create embedding
    embedding = create_embedding(context_text)
    
    # Store in Pinecone with metadata
    metadata = {
        "restaurant_id": restaurant_id,
        "type": "context_cache",
        "name": context_data.get('name', ''),
        "categories": context_data.get('categories', []),
        "item_count": context_data.get('item_count', 0),
        "has_faq": context_data.get('has_faq', False),
        "cached_at": datetime.utcnow().isoformat()
    }
    
    index.upsert(vectors=[{
        "id": context_id,
        "values": embedding,
        "metadata": metadata
    }])
    
    return context_id

# Retrieve cached restaurant context
def get_cached_context(restaurant_id):
    """
    Retrieve cached restaurant context from Pinecone.
    
    Args:
        restaurant_id: Restaurant identifier
        
    Returns:
        Context metadata if found, None otherwise
    """
    # Query for context cache
    results = index.query(
        vector=[0] * 1536,  # Dummy vector for metadata-only query
        top_k=1,
        include_metadata=True,
        filter={
            "restaurant_id": {"$eq": restaurant_id},
            "type": {"$eq": "context_cache"}
        }
    )
    
    if results.matches:
        metadata = results.matches[0].metadata
        # Check if cache is still fresh (24 hours)
        cached_at = datetime.fromisoformat(metadata.get('cached_at'))
        if datetime.utcnow() - cached_at < timedelta(hours=24):
            return metadata
    
    return None
