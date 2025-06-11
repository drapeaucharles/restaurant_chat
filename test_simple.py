#!/usr/bin/env python3.11
"""
Simple test script for the new CRUD and client/chat features.
"""

import requests
import json
import uuid

BASE_URL = "http://localhost:8000"

def test_new_restaurant_routes():
    """Test new restaurant CRUD routes."""
    print("Testing new restaurant CRUD routes...")
    
    # Register a restaurant
    restaurant_data = {
        "restaurant_id": "test_crud_restaurant",
        "password": "test_password",
        "data": {
            "name": "CRUD Test Restaurant",
            "story": "Testing CRUD operations",
            "menu": [],
            "faq": []
        }
    }
    
    response = requests.post(f"{BASE_URL}/restaurant/register", json=restaurant_data)
    print(f"Register Status: {response.status_code}")
    
    # Login
    login_data = {
        "restaurant_id": "test_crud_restaurant",
        "password": "test_password"
    }
    
    response = requests.post(f"{BASE_URL}/restaurant/login", json=login_data)
    token = response.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test PUT profile
    updated_data = {
        "name": "Updated CRUD Restaurant",
        "story": "Updated story",
        "menu": [],
        "faq": []
    }
    
    response = requests.put(f"{BASE_URL}/restaurant/profile", json=updated_data, headers=headers)
    print(f"PUT Profile Status: {response.status_code}")
    print(f"PUT Profile Response: {response.json()}")
    
    # Test DELETE restaurant
    response = requests.delete(f"{BASE_URL}/restaurant/delete", headers=headers)
    print(f"DELETE Restaurant Status: {response.status_code}")
    print(f"DELETE Restaurant Response: {response.json()}")
    
    print("✅ Restaurant CRUD tests completed\n")

def test_client_routes():
    """Test client management routes."""
    print("Testing client management routes...")
    
    # Create a client
    client_data = {
        "restaurant_id": "test_restaurant_123",  # Using existing restaurant
        "name": "Test Client",
        "email": "test@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/clients/", json=client_data)
    print(f"Create Client Status: {response.status_code}")
    if response.status_code == 200:
        print(f"Create Client Response: {response.json()}")
        client_id = response.json()["id"]
        print(f"Created client with ID: {client_id}")
    else:
        print(f"Create Client Error: {response.text}")
    
    print("✅ Client management tests completed\n")

def test_chat_routes():
    """Test chat management routes."""
    print("Testing chat management routes...")
    
    # First create a client
    client_data = {
        "restaurant_id": "test_restaurant_123",
        "name": "Chat Test Client",
        "email": "chat@example.com"
    }
    
    response = requests.post(f"{BASE_URL}/clients/", json=client_data)
    if response.status_code == 200:
        client_id = response.json()["id"]
        
        # Create a chat message
        message_data = {
            "restaurant_id": "test_restaurant_123",
            "client_id": client_id,
            "sender_type": "client",
            "message": "Hello, I'd like to make a reservation"
        }
        
        response = requests.post(f"{BASE_URL}/chat/", json=message_data)
        print(f"Create Message Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Create Message Response: {response.json()}")
        else:
            print(f"Create Message Error: {response.text}")
        
        # Get chat messages
        params = {
            "restaurant_id": "test_restaurant_123",
            "client_id": client_id
        }
        
        response = requests.get(f"{BASE_URL}/chat/", params=params)
        print(f"Get Messages Status: {response.status_code}")
        if response.status_code == 200:
            print(f"Get Messages Response: {response.json()}")
        else:
            print(f"Get Messages Error: {response.text}")
    
    print("✅ Chat management tests completed\n")

def main():
    """Run simple tests."""
    print("🚀 Starting simple API tests...\n")
    
    try:
        test_new_restaurant_routes()
        test_client_routes()
        test_chat_routes()
        
        print("🎉 All simple tests completed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

