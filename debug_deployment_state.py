#!/usr/bin/env python3
"""
Debug current deployment state
"""
import requests
import json

print("Debugging Deployment State")
print("=" * 80)

# 1. Check deployment info
print("\n1. DEPLOYMENT INFO:")
response = requests.get("https://restaurantchat-production.up.railway.app/")
if response.status_code == 200:
    data = response.json()
    deployment = data.get('deployment', {})
    print(json.dumps(deployment, indent=2))

# 2. Check debug endpoints
print("\n2. DEBUG ENDPOINTS:")
endpoints = [
    "/debug/health",
    "/debug/code-version", 
    "/debug/chat-provider"
]

for endpoint in endpoints:
    response = requests.get(f"https://restaurantchat-production.up.railway.app{endpoint}")
    print(f"\n{endpoint}: {response.status_code}")
    if response.status_code == 200:
        print(json.dumps(response.json(), indent=2))

# 3. Check if context debug endpoint exists
print("\n3. PASTA CONTEXT DEBUG:")
response = requests.get("https://restaurantchat-production.up.railway.app/debug/test-pasta-context/bella_vista_restaurant")
print(f"Status: {response.status_code}")
if response.status_code == 200:
    data = response.json()
    print(f"Context being built: {data.get('pasta_context', 'N/A')[:200]}...")
    print(f"Pasta items found: {data.get('pasta_items_found', 'N/A')}")

# 4. Check git commit on server
print("\n4. CHECKING ACTUAL DEPLOYED CODE:")
print("The deployment shows skip_local should be in the code...")
print("But behavior suggests old code is still running")
print("\nPossible issues:")
print("- Deployment cache not updated")
print("- Multiple instances running")
print("- Code not reloaded after deployment")
print("- Environment variable overriding code")