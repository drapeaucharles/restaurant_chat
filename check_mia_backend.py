#!/usr/bin/env python3
"""Check MIA backend health and response times"""
import requests
import time

MIA_BACKEND_URL = "https://mia-backend-production.up.railway.app"

print("🔍 Checking MIA Backend Health\n")

# Test 1: Basic health check
try:
    print("1. Testing basic connectivity...")
    start = time.time()
    response = requests.get(f"{MIA_BACKEND_URL}/", timeout=10)
    elapsed = time.time() - start
    
    if response.status_code == 200:
        print(f"   ✅ Connected in {elapsed:.2f}s")
    else:
        print(f"   ⚠️ Status {response.status_code} in {elapsed:.2f}s")
except Exception as e:
    print(f"   ❌ Connection failed: {e}")

# Test 2: Simple chat request
try:
    print("\n2. Testing chat endpoint...")
    start = time.time()
    response = requests.post(
        f"{MIA_BACKEND_URL}/chat",
        json={
            "message": "Hello",
            "max_tokens": 50
        },
        timeout=30
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        print(f"   ✅ Chat response in {elapsed:.2f}s")
        data = response.json()
        print(f"   Status: {data.get('status')}")
        if data.get('status') == 'completed':
            print(f"   Response: {data.get('response', '')[:100]}...")
    else:
        print(f"   ⚠️ Status {response.status_code} in {elapsed:.2f}s")
        print(f"   Error: {response.text[:200]}")
except requests.exceptions.Timeout:
    print(f"   ❌ Timeout after 30s")
except Exception as e:
    print(f"   ❌ Error: {e}")

# Test 3: Tool-enabled request
try:
    print("\n3. Testing with tools...")
    simple_tool = [{
        "type": "function",
        "function": {
            "name": "test_tool",
            "description": "Test tool",
            "parameters": {"type": "object", "properties": {}}
        }
    }]
    
    start = time.time()
    response = requests.post(
        f"{MIA_BACKEND_URL}/chat",
        json={
            "message": "What is 2+2?",
            "tools": simple_tool,
            "max_tokens": 50
        },
        timeout=30
    )
    elapsed = time.time() - start
    
    if response.status_code == 200:
        print(f"   ✅ Tool response in {elapsed:.2f}s")
    else:
        print(f"   ⚠️ Status {response.status_code} in {elapsed:.2f}s")
except:
    print(f"   ❌ Tool request failed")

print("\n" + "="*60)
print("\nSummary:")
print("- If basic connectivity works but chat is slow, MIA backend is overloaded")
print("- If timeouts occur, there may be network issues")
print("- Heartbeat errors in miner suggest intermittent connectivity")