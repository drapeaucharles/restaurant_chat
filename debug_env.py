#!/usr/bin/env python3
"""
Debug environment variables via API
"""
import requests

def check_environment():
    """Check if MIA_VISA_ENABLED and other visa-related configs are set"""
    
    # Create a simple test endpoint request that might reveal env info
    try:
        # Test if visa routes are available
        response = requests.get("https://restaurantchat-production.up.railway.app/visa/products", timeout=10)
        
        if response.status_code == 200:
            print("✅ Visa routes are available - MIA_VISA_ENABLED=true")
            return True
        elif response.status_code == 404:
            print("❌ Visa routes not found - MIA_VISA_ENABLED=false or routes not loaded")
            return False
        else:
            print(f"⚠️ Visa routes returned {response.status_code}: {response.text[:100]}")
            return False
            
    except Exception as e:
        print(f"❌ Could not test visa routes: {e}")
        return False

if __name__ == "__main__":
    print("🔍 Checking Railway Environment Configuration")
    print("=" * 50)
    
    visa_enabled = check_environment()
    
    if not visa_enabled:
        print("\n🎯 SOLUTION: Set MIA_VISA_ENABLED=true in Railway environment variables")
    else:
        print("\n🎯 Environment looks good - issue is elsewhere")
