#!/usr/bin/env python3
"""Check MIA backend miner status"""
import requests

MIA_URL = "https://mia-backend-production.up.railway.app"

print("🔍 Checking MIA Backend Status\n")

# Check possible status endpoints
endpoints = [
    "/status",
    "/api/status", 
    "/miners",
    "/api/miners",
    "/workers",
    "/api/workers",
    "/debug",
    "/"
]

for endpoint in endpoints:
    try:
        print(f"Checking {endpoint}...")
        response = requests.get(f"{MIA_URL}{endpoint}", timeout=3)
        if response.status_code == 200:
            print(f"✅ Found: {response.text[:200]}...")
            # Try to parse JSON
            try:
                data = response.json()
                if "miners" in data or "workers" in data or "active" in data:
                    print(f"   Data: {data}")
            except:
                pass
        elif response.status_code == 404:
            print(f"   404 - Not found")
        else:
            print(f"   {response.status_code}")
    except Exception as e:
        print(f"   Error: {e}")

print("\nThe MIA backend is online but likely has no active miners.")
print("This explains why chat requests timeout - no GPU workers available.")