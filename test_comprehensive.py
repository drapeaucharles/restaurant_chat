#!/usr/bin/env python3.11
"""
Comprehensive test script for the FastAPI restaurant management application.
Tests all new CRUD operations and client/chat management features.
"""

import requests
import json
import time
import uuid

BASE_URL = "http://localhost:8000"

def test_health():
    """Test health endpoint."""
    print("Testing health endpoint...")
    response = requests.get(f"{BASE_URL}/health")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Health endpoint working\n")

def test_restaurant_registration():
    """Test restaurant registration."""
    print("Testing restaurant registration...")
    
    restaurant_data = {
        "restaurant_id": "test_restaurant_456",
        "password": "secure_password_456",
        "data": {
            "name": "Test Restaurant 2",
            "story": "A test restaurant for comprehensive API testing",
            "menu": [
                {
                    "dish": "Test Pizza",
                    "price": "$15.99",
                    "ingredients": ["dough", "cheese", "tomato"],
                    "description": "A delicious test pizza"
                }
            ],
            "faq": [
                {
                    "question": "Do you deliver?",
                    "answer": "Yes, we deliver for testing!"
                }
            ]
        }
    }
    
    response = requests.post(f"{BASE_URL}/restaurant/register", json=restaurant_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Restaurant registration working\n")
    
    return restaurant_data

def test_restaurant_login(restaurant_data):
    """Test restaurant login."""
    print("Testing restaurant login...")
    
    login_data = {
        "restaurant_id": restaurant_data["restaurant_id"],
        "password": restaurant_data["password"]
    }
    
    response = requests.post(f"{BASE_URL}/restaurant/login", json=login_data)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    
    token = response.json()["access_token"]
    print("✅ Restaurant login working\n")
    
    return token

def test_restaurant_profile_crud(token, restaurant_data):
    """Test restaurant profile CRUD operations."""
    print("Testing restaurant profile CRUD...")
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # Test GET profile
    response = requests.get(f"{BASE_URL}/restaurant/profile", headers=headers)
    print(f"GET Profile Status: {response.status_code}")
    print(f"GET Profile Response: {response.json()}")
    assert response.status_code == 200
    
    # Test PUT profile
    updated_data = {
        "name": "Updated Test Restaurant",
        "story": "Updated story for testing",
        "menu": [
            {
                "dish": "Updated Pizza",
                "price": "$18.99",
                "ingredients": ["dough", "cheese", "tomato", "pepperoni"],
                "description": "An updated delicious pizza"
            }
        ],
        "faq": [
            {
                "question": "Are you updated?",
                "answer": "Yes, we are updated!"
            }
        ]
    }
    
    response = requests.put(f"{BASE_URL}/restaurant/profile", json=updated_data, headers=headers)
    print(f"PUT Profile Status: {response.status_code}")
    print(f"PUT Profile Response: {response.json()}")
    assert response.status_code == 200
    
    print("✅ Restaurant profile CRUD working\n")

def test_client_management(restaurant_data):
    """Test client management."""
    print("Testing client management...")
    
    # Create a client
    client_data = {
        "restaurant_id": restaurant_data["restaurant_id"],
        "name": "Test Client",
        "email": "test@example.com",
        "preferences": {"dietary": "vegetarian"}
    }
    
    response = requests.post(f"{BASE_URL}/clients/", json=client_data)
    print(f"Create Client Status: {response.status_code}")
    print(f"Create Client Response: {response.json()}")
    assert response.status_code == 200
    
    client_id = response.json()["id"]
    print(f"Created client with ID: {client_id}")
    print("✅ Client creation working\n")
    
    return client_id

def test_protected_client_list(token):
    """Test protected client list endpoint."""
    print("Testing protected client list...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/clients/", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Protected client list working\n")

def test_chat_management(restaurant_data, client_id):
    """Test chat management."""
    print("Testing chat management...")
    
    # Create a chat message from client
    message_data = {
        "restaurant_id": restaurant_data["restaurant_id"],
        "client_id": client_id,
        "sender_type": "client",
        "message": "Hello, I'd like to make a reservation"
    }
    
    response = requests.post(f"{BASE_URL}/chat/", json=message_data)
    print(f"Create Message Status: {response.status_code}")
    print(f"Create Message Response: {response.json()}")
    assert response.status_code == 200
    
    # Create a response from restaurant
    response_data = {
        "restaurant_id": restaurant_data["restaurant_id"],
        "client_id": client_id,
        "sender_type": "restaurant",
        "message": "Of course! What time would you prefer?"
    }
    
    response = requests.post(f"{BASE_URL}/chat/", json=response_data)
    print(f"Create Response Status: {response.status_code}")
    print(f"Create Response Response: {response.json()}")
    assert response.status_code == 200
    
    # Get chat messages
    params = {
        "restaurant_id": restaurant_data["restaurant_id"],
        "client_id": client_id
    }
    
    response = requests.get(f"{BASE_URL}/chat/", params=params)
    print(f"Get Messages Status: {response.status_code}")
    print(f"Get Messages Response: {response.json()}")
    assert response.status_code == 200
    assert len(response.json()) == 2  # Should have 2 messages
    
    print("✅ Chat management working\n")

def test_restaurant_deletion(token):
    """Test restaurant deletion."""
    print("Testing restaurant deletion...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.delete(f"{BASE_URL}/restaurant/delete", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Restaurant deletion working\n")

def main():
    """Run all tests."""
    print("🚀 Starting comprehensive API tests...\n")
    
    try:
        # Test basic functionality
        test_health()
        
        # Test registration and authentication flow
        restaurant_data = test_restaurant_registration()
        token = test_restaurant_login(restaurant_data)
        
        # Test restaurant CRUD operations
        test_restaurant_profile_crud(token, restaurant_data)
        
        # Test client management
        client_id = test_client_management(restaurant_data)
        test_protected_client_list(token)
        
        # Test chat management
        test_chat_management(restaurant_data, client_id)
        
        # Test restaurant deletion (do this last)
        test_restaurant_deletion(token)
        
        print("🎉 All comprehensive tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    main()

