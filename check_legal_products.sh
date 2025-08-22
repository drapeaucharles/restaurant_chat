#!/bin/bash

# Check legal business products in Railway database
# Usage: ./check_legal_products.sh

API_URL="https://restaurant-backend-production-96b5.up.railway.app"

echo "Checking Legal Business Products"
echo "================================"

# Test search debug endpoint
echo -e "\n1. Testing search for 'Remote Worker KITAS'"
curl -X POST "$API_URL/debug/search" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "bali-legal-consulting",
    "query": "Remote Worker KITAS"
  }' | jq .

echo -e "\n2. Testing search for 'visa'"
curl -X POST "$API_URL/debug/search" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "bali-legal-consulting",
    "query": "visa"
  }' | jq .

echo -e "\n3. Testing search for 'retirement'"
curl -X POST "$API_URL/debug/search" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "bali-legal-consulting",
    "query": "retirement"
  }' | jq .

echo -e "\n4. Testing search for 'company formation'"
curl -X POST "$API_URL/debug/search" \
  -H "Content-Type: application/json" \
  -d '{
    "business_id": "bali-legal-consulting",
    "query": "company formation"
  }' | jq .