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
