#!/bin/bash
# Check businesses table for RestoLorenzo

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔍 Checking businesses table for Lorenzo..."
psql "$DATABASE_URL" -c "
SELECT business_id, 
       data->>'business_name' as name
FROM businesses 
WHERE LOWER(data->>'business_name') LIKE '%lorenzo%'
   OR LOWER(business_id) LIKE '%lorenzo%'
LIMIT 10;
"