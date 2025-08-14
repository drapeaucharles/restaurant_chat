#!/usr/bin/env python3
"""
Quick test to verify RAG deployment
"""
import requests
import json
import time
import uuid

BASE_URL = "https://restaurantchat-production.up.railway.app"

def check_deployment():
    """Check if new version is deployed"""
    print("🔍 Checking deployment status...")
    response = requests.get(f"{BASE_URL}/", timeout=10)
    if response.status_code == 200:
        data = response.json()
        version = data['deployment']['version']
        print(f"✅ Current version: {version}")
        return 'v7-rag-lightweight' in version
    return False

def test_provider():
    """Check if RAG is enabled"""
    print("\n🤖 Checking chat provider...")
    response = requests.get(f"{BASE_URL}/provider", timeout=10)
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Provider: {data['provider']}")
        print(f"✅ RAG enabled: {data.get('rag_enabled', False)}")
        return data.get('rag_enabled', False)
    return False

def test_embeddings_endpoint():
    """Test if embeddings endpoint exists"""
    print("\n📊 Testing embeddings endpoint...")
    response = requests.get(f"{BASE_URL}/embeddings/stats", timeout=10)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"✅ Embeddings endpoint working!")
        print(f"   Total items indexed: {data.get('total_items', 0)}")
        return True
    return False

def test_chat_with_rag():
    """Test chat endpoint"""
    print("\n💬 Testing chat with semantic query...")
    client_id = str(uuid.uuid4())
    
    response = requests.post(
        f"{BASE_URL}/chat",
        json={
            "restaurant_id": "bella_vista_restaurant",
            "client_id": client_id,
            "sender_type": "client",
            "message": "I'm looking for something healthy and vegetarian"
        },
        timeout=30
    )
    
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        answer = data.get("answer", "")
        if answer:
            print(f"✅ Got response: {answer[:150]}...")
            return True
        else:
            print("⚠️  Empty response")
    else:
        print(f"❌ Error: {response.text[:200]}")
    return False

def main():
    print("🚀 RAG Deployment Test")
    print("=" * 50)
    
    # Wait for deployment if needed
    if not check_deployment():
        print("\n⏳ Waiting for deployment to complete...")
        print("   This may take 5-10 minutes for first deployment")
        print("   Check Railway dashboard for progress")
        return
    
    # Test RAG features
    rag_enabled = test_provider()
    embeddings_working = test_embeddings_endpoint()
    
    if rag_enabled:
        print("\n✅ RAG is enabled!")
        
        if not embeddings_working:
            print("\n📝 Next steps:")
            print("1. Run database migration:")
            print("   railway run python run_migrations.py")
            print("2. Index menu items:")
            print("   railway run python index_menu_local.py")
    else:
        print("\n⚠️  RAG not enabled yet")
        print("Check environment variables in Railway")
    
    # Test chat anyway
    test_chat_with_rag()

if __name__ == "__main__":
    main()