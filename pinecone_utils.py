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
    content_text = "\n".join([
        content_dict.get("name", ""),
        content_dict.get("story", ""),
        "\n".join([
            item.get("dish", "") + " " + item.get("description", "")
            for item in content_dict.get("menu", [])
        ]),
        "\n".join([
            faq.get("question", "") + " " + faq.get("answer", "")
            for faq in content_dict.get("faq", [])
        ])
    ])

    embedding = create_embedding(content_text)

    index.upsert([
        (f"restaurant_{restaurant_id}", embedding)
    ])

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
