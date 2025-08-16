#!/bin/bash

echo "Testing Hybrid Smart RAG..."

# Test 1: Simple query
echo -e "\n1. Simple Query (should use optimized):"
curl -s -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d @- <<EOF | jq -r '.answer' | head -c 100
{
  "restaurant_id": "bella_vista_restaurant",
  "client_id": "test-123",
  "sender_type": "client",
  "message": "Hi there!"
}
EOF

# Test 2: Complex query
echo -e "\n\n2. Complex Query (should use enhanced_v2):"
curl -s -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d @- <<EOF | jq -r '.answer' | head -c 150
{
  "restaurant_id": "bella_vista_restaurant",
  "client_id": "test-123",
  "sender_type": "client",
  "message": "I am vegetarian but also allergic to nuts, what can I eat?"
}
EOF

echo -e "\n\nDone!"