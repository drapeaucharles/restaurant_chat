#!/bin/bash
# Remove WhatsApp from RestoLorenzo

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔧 Removing WhatsApp from RestoLorenzo..."

# First, check if RestoLorenzo exists and show current whatsapp_config
psql "$DATABASE_URL" -c "
SELECT restaurant_id, business_name, whatsapp_config 
FROM restaurants 
WHERE business_name = 'RestoLorenzo';
"

# Remove WhatsApp configuration
psql "$DATABASE_URL" -c "
UPDATE restaurants 
SET whatsapp_config = NULL,
    updated_at = CURRENT_TIMESTAMP
WHERE business_name = 'RestoLorenzo';
"

# Verify the change
echo -e "\n✅ Verifying the change..."
psql "$DATABASE_URL" -c "
SELECT restaurant_id, business_name, whatsapp_config 
FROM restaurants 
WHERE business_name = 'RestoLorenzo';
"

echo -e "\n✅ WhatsApp configuration removed from RestoLorenzo"