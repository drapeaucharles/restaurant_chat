#!/bin/bash
# Remove WhatsApp from RestoLorenzo

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔍 Finding RestoLorenzo..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, 
       data->>'business_name' as name, 
       whatsapp_number,
       whatsapp_session_id
FROM restaurants 
WHERE data->>'business_name' = 'RestoLorenzo'
   OR restaurant_id = 'RestoLorenzo';
"

echo -e "\n🔧 Removing WhatsApp data from RestoLorenzo..."
psql "$DATABASE_URL" -c "
UPDATE restaurants 
SET whatsapp_number = NULL,
    whatsapp_session_id = NULL
WHERE data->>'business_name' = 'RestoLorenzo'
   OR restaurant_id = 'RestoLorenzo';
"

echo -e "\n✅ Verifying the change..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, 
       data->>'business_name' as name, 
       whatsapp_number,
       whatsapp_session_id
FROM restaurants 
WHERE data->>'business_name' = 'RestoLorenzo'
   OR restaurant_id = 'RestoLorenzo';
"

echo -e "\n✅ WhatsApp data removed from RestoLorenzo"