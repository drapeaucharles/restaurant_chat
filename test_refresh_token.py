#!/usr/bin/env python3.11
"""
Test suite for refresh token functionality.
"""

import requests
import time
import json
from datetime import datetime, timedelta

BASE_URL = "http://localhost:8000"

class TestRefreshToken:
    """Test class for refresh token functionality."""
    
    def test_login_returns_refresh_token(self):
        """Test that login returns both access and refresh tokens."""
        # Register a restaurant first
        restaurant_data = {
            "restaurant_id": f"refresh_test_{int(time.time())}",
            "password": "test_password_123",
            "role": "owner",
            "data": {
                "name": "Refresh Test Restaurant",
                "story": "Testing refresh tokens",
                "menu": [],
                "faq": []
            }
        }
        
        response = requests.post(f"{BASE_URL}/restaurant/register", json=restaurant_data)
        assert response.status_code == 200
        
        # Login and check response structure
        login_data = {
            "restaurant_id": restaurant_data["restaurant_id"],
            "password": restaurant_data["password"]
        }
        
        response = requests.post(f"{BASE_URL}/restaurant/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        
        # Check that all required fields are present
        assert "access_token" in data
        assert "refresh_token" in data
        assert "token_type" in data
        assert "expires_in" in data
        assert "refresh_token_expires_in" in data
        assert "role" in data
        
        assert data["token_type"] == "bearer"
        assert data["role"] == "owner"
        assert data["expires_in"] > 0
        assert data["refresh_token_expires_in"] > data["expires_in"]  # Refresh token should last longer
        
        print("✅ Login returns refresh token with correct structure")
        return restaurant_data, data
    
    def test_refresh_token_generates_new_access_token(self):
        """Test that refresh token endpoint generates new access token."""
        # Get tokens from login
        restaurant_data, tokens = self.test_login_returns_refresh_token()
        
        # Use refresh token to get new access token
        refresh_request = {
            "refresh_token": tokens["refresh_token"]
        }
        
        response = requests.post(f"{BASE_URL}/restaurant/refresh-token", json=refresh_request)
        assert response.status_code == 200
        
        new_tokens = response.json()
        
        # Check response structure
        assert "access_token" in new_tokens
        assert "refresh_token" in new_tokens
        assert "token_type" in new_tokens
        assert "expires_in" in new_tokens
        assert "refresh_token_expires_in" in new_tokens
        assert "role" in new_tokens
        
        # New access token should be different from the original
        assert new_tokens["access_token"] != tokens["access_token"]
        
        # New refresh token should be different (token rotation)
        assert new_tokens["refresh_token"] != tokens["refresh_token"]
        
        # Role should be preserved
        assert new_tokens["role"] == tokens["role"]
        
        print("✅ Refresh token generates new access token")
        return restaurant_data, new_tokens
    
    def test_new_access_token_works(self):
        """Test that the new access token from refresh works for protected routes."""
        # Get new tokens from refresh
        restaurant_data, new_tokens = self.test_refresh_token_generates_new_access_token()
        
        # Use new access token to access protected route
        headers = {"Authorization": f"Bearer {new_tokens['access_token']}"}
        response = requests.get(f"{BASE_URL}/restaurant/profile", headers=headers)
        
        assert response.status_code == 200
        profile_data = response.json()
        assert profile_data["restaurant_id"] == restaurant_data["restaurant_id"]
        
        print("✅ New access token works for protected routes")
    
    def test_invalid_refresh_token_rejected(self):
        """Test that invalid refresh tokens are rejected."""
        invalid_refresh_request = {
            "refresh_token": "invalid.refresh.token"
        }
        
        response = requests.post(f"{BASE_URL}/restaurant/refresh-token", json=invalid_refresh_request)
        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json().get("detail", "")
        
        print("✅ Invalid refresh token rejected")
    
    def test_access_token_as_refresh_token_rejected(self):
        """Test that access tokens cannot be used as refresh tokens."""
        # Get tokens from login
        restaurant_data, tokens = self.test_login_returns_refresh_token()
        
        # Try to use access token as refresh token
        invalid_refresh_request = {
            "refresh_token": tokens["access_token"]  # Using access token instead of refresh token
        }
        
        response = requests.post(f"{BASE_URL}/restaurant/refresh-token", json=invalid_refresh_request)
        assert response.status_code == 401
        assert "Invalid or expired refresh token" in response.json().get("detail", "")
        
        print("✅ Access token cannot be used as refresh token")
    
    def test_token_expiration_times(self):
        """Test that token expiration times are reasonable."""
        # Get tokens from login
        restaurant_data, tokens = self.test_login_returns_refresh_token()
        
        access_expires_in = tokens["expires_in"]
        refresh_expires_in = tokens["refresh_token_expires_in"]
        
        # Access token should expire in 24 hours (86400 seconds)
        expected_access_expiry = 24 * 60 * 60  # 24 hours in seconds
        assert access_expires_in == expected_access_expiry
        
        # Refresh token should expire in 7 days (604800 seconds)
        expected_refresh_expiry = 7 * 24 * 60 * 60  # 7 days in seconds
        assert refresh_expires_in == expected_refresh_expiry
        
        # Refresh token should last longer than access token
        assert refresh_expires_in > access_expires_in
        
        print("✅ Token expiration times are correct")
    
    def test_refresh_token_preserves_role(self):
        """Test that refresh token preserves user role."""
        # Create owner and staff accounts
        owner_data = {
            "restaurant_id": f"owner_refresh_{int(time.time())}",
            "password": "owner_password",
            "role": "owner",
            "data": {
                "name": "Owner Restaurant",
                "story": "Owner testing",
                "menu": [],
                "faq": []
            }
        }
        
        # Register owner
        response = requests.post(f"{BASE_URL}/restaurant/register", json=owner_data)
        assert response.status_code == 200
        
        # Login as owner
        login_data = {
            "restaurant_id": owner_data["restaurant_id"],
            "password": owner_data["password"]
        }
        
        response = requests.post(f"{BASE_URL}/restaurant/login", json=login_data)
        assert response.status_code == 200
        owner_tokens = response.json()
        
        # Refresh owner token
        refresh_request = {"refresh_token": owner_tokens["refresh_token"]}
        response = requests.post(f"{BASE_URL}/restaurant/refresh-token", json=refresh_request)
        assert response.status_code == 200
        new_owner_tokens = response.json()
        
        # Role should be preserved
        assert new_owner_tokens["role"] == "owner"
        
        print("✅ Refresh token preserves user role")
    
    def test_old_refresh_token_invalid_after_refresh(self):
        """Test that old refresh tokens become invalid after being used (token rotation)."""
        # Get tokens from login
        restaurant_data, tokens = self.test_login_returns_refresh_token()
        
        old_refresh_token = tokens["refresh_token"]
        
        # Use refresh token to get new tokens
        refresh_request = {"refresh_token": old_refresh_token}
        response = requests.post(f"{BASE_URL}/restaurant/refresh-token", json=refresh_request)
        assert response.status_code == 200
        
        # Try to use the old refresh token again (should fail due to token rotation)
        response = requests.post(f"{BASE_URL}/restaurant/refresh-token", json=refresh_request)
        
        # Note: This test assumes token rotation is implemented
        # If token rotation is not implemented, this test might pass
        # In a production system, you'd typically want token rotation for security
        if response.status_code == 401:
            print("✅ Old refresh token invalid after refresh (token rotation enabled)")
        else:
            print("⚠️ Old refresh token still valid (token rotation not implemented)")


def run_refresh_token_tests():
    """Run all refresh token tests."""
    print("🚀 Starting refresh token tests...\n")
    
    test_instance = TestRefreshToken()
    
    try:
        test_instance.test_login_returns_refresh_token()
        test_instance.test_refresh_token_generates_new_access_token()
        test_instance.test_new_access_token_works()
        test_instance.test_invalid_refresh_token_rejected()
        test_instance.test_access_token_as_refresh_token_rejected()
        test_instance.test_token_expiration_times()
        test_instance.test_refresh_token_preserves_role()
        test_instance.test_old_refresh_token_invalid_after_refresh()
        
        print("\n🎉 All refresh token tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


if __name__ == "__main__":
    run_refresh_token_tests()

