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
    """Test restaurant registration with password hashing."""
    print("Testing restaurant registration with password hashing...")
    
    restaurant_data = {
        "restaurant_id": "test_restaurant_new",
        "password": "secure_password_new",
        "data": {
            "name": "New Test Restaurant",
            "story": "A new test restaurant for API testing",
            "menu": [],
            "faq": []
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

def main():
    """Run all tests."""
    print("🚀 Starting API tests...\n")
    
    try:
        # Test basic functionality
        test_health()
        
        # Test registration and authentication flow
        restaurant_data = test_restaurant_registration()
        token = test_restaurant_login(restaurant_data)
        
        print("🎉 All tests passed!")
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()

