#!/bin/bash

# Test legal business chat API
# Usage: ./test_legal_chat_api.sh [API_URL]

API_URL="${1:-https://restaurant-backend-production-96b5.up.railway.app}"

echo "Testing Legal Business Chat at: $API_URL"
echo "================================"

# Test 1: Remote Worker KITAS
echo -e "\n1. Testing: Remote Worker KITAS query"
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "I need a Remote Worker KITAS visa",
    "client_id": "test_legal_123"
  }' | jq .

sleep 1

# Test 2: Retirement visa cost
echo -e "\n2. Testing: Retirement visa cost"
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "How much does the retirement visa cost?",
    "client_id": "test_legal_123"
  }' | jq .

sleep 1

# Test 3: Company setup
echo -e "\n3. Testing: Company setup"
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "I want to set up a company in Bali",
    "client_id": "test_legal_123"
  }' | jq .

sleep 1

# Test 4: Digital nomad services
echo -e "\n4. Testing: Digital nomad services"
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "What services do you offer for digital nomads?",
    "client_id": "test_legal_123"
  }' | jq .

sleep 1

# Test 5: General visa services
echo -e "\n5. Testing: General visa services"
curl -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "Tell me about your visa services",
    "client_id": "test_legal_123"
  }' | jq .

echo -e "\n\nTest complete!"