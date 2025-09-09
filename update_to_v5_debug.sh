#!/bin/bash
# Temporarily update restaurant to use V5 debug mode

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔧 Updating restaurant to use V5 DEBUG mode..."

# Update Bella Vista to V5 debug
psql "$DATABASE_URL" -c "
UPDATE restaurants 
SET rag_mode = 'internal_tools_v5_debug'
WHERE restaurant_id = 'bella_vista_restaurant';
"

echo "✅ Restaurant updated to V5 DEBUG mode!"