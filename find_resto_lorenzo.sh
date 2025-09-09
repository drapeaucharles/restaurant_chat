#!/bin/bash
# Find RestoLorenzo in database

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔍 Looking for RestoLorenzo in data JSON..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, data->>'business_name' as name, whatsapp_config
FROM restaurants 
WHERE data->>'business_name' LIKE '%Lorenzo%' 
   OR data->>'business_name' LIKE '%Resto%'
   OR restaurant_id LIKE '%lorenzo%';
"

echo -e "\n🔍 Checking whatsapp_config column..."
psql "$DATABASE_URL" -c "
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'restaurants' 
AND column_name LIKE '%whatsapp%';
"