#!/bin/bash
# Check WhatsApp sessions table

DATABASE_URL="postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

echo "🔍 Checking whatsapp_sessions table for RestoLorenzo..."
psql "$DATABASE_URL" -c "
SELECT session_id, created_at, updated_at
FROM whatsapp_sessions 
WHERE session_id = 'RestoLorenzo';
"

echo -e "\n📋 All WhatsApp sessions:"
psql "$DATABASE_URL" -c "
SELECT session_id, created_at, updated_at
FROM whatsapp_sessions
ORDER BY created_at DESC;
"

echo -e "\n🗑️ Removing RestoLorenzo from whatsapp_sessions..."
psql "$DATABASE_URL" -c "
DELETE FROM whatsapp_sessions 
WHERE session_id = 'RestoLorenzo';
"

echo -e "\n✅ Verifying removal..."
psql "$DATABASE_URL" -c "
SELECT session_id FROM whatsapp_sessions;
"