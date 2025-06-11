#!/usr/bin/env python3.11
"""
Test script for the FastAPI restaurant management application.
"""

import requests
import json
import time

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
        "restaurant_id": "test_restaurant_123",
        "password": "secure_password_123",
        "data": {
            "name": "Test Restaurant",
            "story": "A test restaurant for API testing",
            "menu": [
                {
                    "dish": "Test Burger",
                    "price": "$12.99",
                    "ingredients": ["beef", "lettuce", "tomato"],
                    "description": "A delicious test burger"
                }
            ],
            "faq": [
                {
                    "question": "Are you open?",
                    "answer": "Yes, we are open for testing!"
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

def test_protected_route(token, restaurant_id):
    """Test protected route with authentication."""
    print("Testing protected route (restaurant profile)...")
    
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/restaurant/profile", headers=headers)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Protected route working\n")

def test_public_route(restaurant_id):
    """Test public route (restaurant info)."""
    print("Testing public route (restaurant info)...")
    
    response = requests.get(f"{BASE_URL}/restaurant/info?restaurant_id={restaurant_id}")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 200
    print("✅ Public route working\n")

def test_unauthorized_access():
    """Test unauthorized access to protected route."""
    print("Testing unauthorized access...")
    
    response = requests.get(f"{BASE_URL}/restaurant/profile")
    print(f"Status: {response.status_code}")
    print(f"Response: {response.json()}")
    assert response.status_code == 401
    print("✅ Unauthorized access properly blocked\n")

def main():
    """Run all tests."""
    print("🚀 Starting API tests...\n")
    
    try:
        # Test basic functionality
        test_health()
        
        # Test registration and authentication flow
        restaurant_data = test_restaurant_registration()
        token = test_restaurant_login(restaurant_data)
        
        # Test protected and public routes
        test_protected_route(token, restaurant_data["restaurant_id"])
        test_public_route(restaurant_data["restaurant_id"])
        
        # Test security
        test_unauthorized_access()
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

