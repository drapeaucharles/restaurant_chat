#!/bin/bash
# Check RestoLorenzo in database

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔍 Checking restaurants table schema..."
psql "$DATABASE_URL" -c "\d restaurants" | head -20

echo -e "\n🔍 Looking for RestoLorenzo..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, restaurant_name, whatsapp_config 
FROM restaurants 
WHERE restaurant_name LIKE '%Lorenzo%' OR restaurant_name LIKE '%Resto%';
"