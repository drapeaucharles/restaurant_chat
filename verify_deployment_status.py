#!/usr/bin/env python3
"""Verify the deployment status and configuration"""
import requests
import time

BACKEND_URL = "https://restaurantchat-production.up.railway.app"

print("🔍 Checking deployment status...\n")

# Check version to see if new deployment is active
response = requests.get(f"{BACKEND_URL}/version")
if response.status_code == 200:
    version_data = response.json()
    print(f"Version: {version_data}")
    
# Check provider info
try:
    response = requests.get(f"{BACKEND_URL}/chat/provider")
    if response.status_code == 200:
        provider_data = response.json()
        print(f"\nChat Provider:")
        print(f"  Default mode: {provider_data.get('default_mode')}")
        print(f"  Available modes: {len(provider_data.get('available_modes', []))} modes")
        
        # Check if internal_tools_v3 is available
        modes = provider_data.get('available_modes', [])
        if 'internal_tools_v3' in modes:
            print("  ✅ internal_tools_v3 is available!")
        else:
            print("  ❌ internal_tools_v3 is NOT in available modes")
            
        if provider_data.get('default_mode') == 'internal_tools_v3':
            print("  ✅ DEFAULT_RAG_MODE is set to internal_tools_v3!")
        else:
            print(f"  ⚠️ DEFAULT_RAG_MODE is still: {provider_data.get('default_mode')}")
except:
    pass

print("\nIf the default mode is not internal_tools_v3, the deployment may still be in progress.")
print("Railway typically takes 1-3 minutes to deploy after environment changes.")