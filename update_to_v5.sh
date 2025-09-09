#!/bin/bash
# Update restaurant to use internal_tools_v5

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔧 Updating restaurant to use V5 (concise responses)..."

# Find and update Bella Vista Trattoria to V5
psql "$DATABASE_URL" -c "
UPDATE restaurants 
SET rag_mode = 'internal_tools_v5'
WHERE restaurant_id = 'bella_vista_restaurant';
"

# Check the update
echo -e "\n✅ Verifying update..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, rag_mode
FROM restaurants 
WHERE restaurant_id = 'bella_vista_restaurant';
"

echo -e "\n✅ Restaurant updated to use V5 with concise responses!"