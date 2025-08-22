#!/bin/bash

# Complete test for legal business functionality
# Usage: ./test_legal_complete.sh [API_URL]

API_URL="${1:-https://restaurant-backend-production-96b5.up.railway.app}"

echo "Complete Legal Business Test"
echo "API URL: $API_URL"
echo "============================="

# Check if business and products exist
echo -e "\n1. Checking if legal business exists..."
curl -s "$API_URL/debug/business/bali-legal-consulting/products" | jq .

# Test search functionality
echo -e "\n\n2. Testing search functionality..."
echo -e "\n2a. Search for 'Remote Worker KITAS':"
curl -s -X POST "$API_URL/debug/search" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "bali-legal-consulting",
    "query": "Remote Worker KITAS"
  }' | jq .

# Test actual chat
echo -e "\n\n3. Testing chat responses..."
echo -e "\n3a. Query: 'I need a Remote Worker KITAS visa'"
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "I need a Remote Worker KITAS visa",
    "client_id": "test_legal_123"
  }' | jq .

echo -e "\n3b. Query: 'How much does the retirement visa cost?'"
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "How much does the retirement visa cost?",
    "client_id": "test_legal_123"
  }' | jq .

echo -e "\n3c. Query: 'What services do you offer?'"
curl -s -X POST "$API_URL/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bali-legal-consulting",
    "message": "What services do you offer?",
    "client_id": "test_legal_123"
  }' | jq .

echo -e "\n\nTest complete!"