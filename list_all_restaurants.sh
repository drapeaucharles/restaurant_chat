#!/bin/bash
# List all restaurants

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "📋 Listing all restaurants with WhatsApp data..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, 
       data->>'business_name' as name, 
       whatsapp_number,
       whatsapp_session_id
FROM restaurants 
WHERE whatsapp_number IS NOT NULL 
   OR whatsapp_session_id IS NOT NULL
ORDER BY restaurant_id;
"

echo -e "\n📋 Searching for any restaurant with 'Lorenzo' in name..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, 
       data->>'business_name' as name
FROM restaurants 
WHERE LOWER(data->>'business_name') LIKE '%lorenzo%'
   OR LOWER(restaurant_id) LIKE '%lorenzo%';
"