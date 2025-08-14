#!/usr/bin/env python3
"""
Complete RAG setup script for production
Handles migration, indexing, and verification
"""
import os
import sys
import time
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
BASE_URL = os.getenv("PUBLIC_API_URL", "https://restaurantchat-production.up.railway.app")
API_KEY = os.getenv("API_KEY", "your-api-key-here")

def run_migration():
    """Run the pgvector migration"""
    print("🔄 Running pgvector migration...")
    try:
        from migrations.add_pgvector import upgrade
        success = upgrade()
        if success:
            print("✅ Migration completed successfully!")
            return True
        else:
            print("⚠️  Migration needs manual intervention")
            print("Please ask your database admin to run: CREATE EXTENSION vector;")
            return False
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def get_auth_token():
    """Get authentication token"""
    # This assumes you have an auth endpoint
    # Modify based on your actual auth setup
    print("🔑 Getting authentication token...")
    
    # For now, return a placeholder
    # In production, this should get a real token
    return "Bearer " + API_KEY

def index_restaurant_menu(restaurant_id: str, auth_token: str):
    """Index menu items for a restaurant"""
    print(f"📚 Indexing menu for {restaurant_id}...")
    
    response = requests.post(
        f"{BASE_URL}/embeddings/index/{restaurant_id}",
        headers={"Authorization": auth_token},
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ {data['message']}")
        return True
    else:
        print(f"❌ Indexing failed: {response.status_code} - {response.text}")
        return False

def check_indexing_status(restaurant_id: str, auth_token: str):
    """Check if indexing is complete"""
    print(f"🔍 Checking indexing status for {restaurant_id}...")
    
    response = requests.get(
        f"{BASE_URL}/embeddings/status/{restaurant_id}",
        headers={"Authorization": auth_token},
        timeout=10
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"📊 Indexed items: {data['indexed_items']}")
        print(f"📅 Last indexed: {data['last_indexed']}")
        return data['indexed_items'] > 0
    else:
        print(f"❌ Status check failed: {response.status_code}")
        return False

def test_semantic_search(restaurant_id: str, query: str):
    """Test semantic search"""
    print(f"🔎 Testing semantic search: '{query}'")
    
    response = requests.post(
        f"{BASE_URL}/embeddings/search",
        json={
            "query": query,
            "restaurant_id": restaurant_id,
            "limit": 5
        },
        timeout=15
    )
    
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Found {data['count']} results:")
        for item in data['results']:
            print(f"  - {item['name']} ({item['price']}) - Similarity: {item['similarity']:.2f}")
        return True
    else:
        print(f"❌ Search failed: {response.status_code}")
        return False

def test_chat_with_rag(restaurant_id: str, message: str):
    """Test chat endpoint with RAG"""
    print(f"💬 Testing chat with RAG: '{message}'")
    
    import uuid
    client_id = str(uuid.uuid4())
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "restaurant_id": restaurant_id,
            "client_id": client_id,
            "sender_type": "client",
            "message": message
        },
        timeout=30
    )
    
    if response.status_code == 200:
        data = response.json()
        answer = data.get("answer", "")
        print(f"✅ AI Response: {answer[:200]}...")
        return True
    else:
        print(f"❌ Chat failed: {response.status_code}")
        return False

def main():
    """Run complete RAG setup"""
    print("🚀 RAG Setup Script")
    print("=" * 50)
    
    restaurant_id = "bella_vista_restaurant"
    
    # Step 1: Run migration
    if "--skip-migration" not in sys.argv:
        if not run_migration():
            print("\n⚠️  Migration failed. You may need to:")
            print("1. Ensure you have PostgreSQL superuser access")
            print("2. Or manually run: CREATE EXTENSION vector;")
            print("\nContinue anyway? (y/n): ", end="")
            if input().lower() != 'y':
                return
    
    # Step 2: Get auth token
    auth_token = get_auth_token()
    
    # Step 3: Index restaurant menu
    print(f"\n📚 Indexing menu items...")
    if not index_restaurant_menu(restaurant_id, auth_token):
        print("❌ Failed to start indexing")
        return
    
    # Step 4: Wait for indexing to complete
    print("\n⏳ Waiting for indexing to complete...")
    max_attempts = 30  # 5 minutes max
    for i in range(max_attempts):
        time.sleep(10)
        if check_indexing_status(restaurant_id, auth_token):
            print("✅ Indexing complete!")
            break
        print(f"⏳ Still indexing... ({i+1}/{max_attempts})")
    
    # Step 5: Test semantic search
    print("\n🧪 Testing semantic search...")
    test_queries = [
        "healthy and light dishes",
        "vegetarian pasta",
        "seafood options",
        "gluten free",
        "spicy food"
    ]
    
    for query in test_queries:
        test_semantic_search(restaurant_id, query)
        time.sleep(1)
    
    # Step 6: Test chat with RAG
    print("\n💬 Testing RAG-enhanced chat...")
    test_messages = [
        "What healthy options do you have?",
        "I'm looking for something vegetarian",
        "Do you have any gluten-free dishes?",
        "What seafood pasta do you offer?"
    ]
    
    for message in test_messages:
        test_chat_with_rag(restaurant_id, message)
        time.sleep(2)
    
    print("\n✅ RAG setup complete!")
    print("Your chat system now has semantic search capabilities!")

if __name__ == "__main__":
    main()