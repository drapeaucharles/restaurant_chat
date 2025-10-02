-- Fix Missing Restaurants Script
-- Based on investigation, restore the restaurants that have chat activity

\echo '🔧 FIXING MISSING RESTAURANTS...'
\echo ''

-- First, let's see what we're working with
\echo '📊 Current restaurants table:'
SELECT restaurant_id, role, data->>'name' as name FROM restaurants ORDER BY role, restaurant_id;

\echo ''
\echo '💬 Restaurants with chat activity but missing from restaurants table:'
SELECT DISTINCT cm.restaurant_id, COUNT(*) as message_count
FROM chat_messages cm
LEFT JOIN restaurants r ON cm.restaurant_id = r.restaurant_id
WHERE r.restaurant_id IS NULL
  AND cm.restaurant_id NOT IN ('admin', 'admin@admin.com')
GROUP BY cm.restaurant_id
ORDER BY message_count DESC;

\echo ''
\echo '🔧 RESTORING MISSING RESTAURANTS...'

-- Restore bella_vista_restaurant (7230 messages - clearly a real restaurant!)
INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
VALUES (
    'bella_vista_restaurant', 
    'temp_password_2025', 
    'owner', 
    '{"name": "Bella Vista Restaurant", "description": "Restored from chat history - 7230 messages", "restored": true, "restoration_date": "2025-10-02"}',
    'italian',
    'dynamic',
    'restaurant'
) ON CONFLICT (restaurant_id) DO NOTHING;

-- Restore RestoBulla (87 messages)
INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
VALUES (
    'RestoBulla', 
    'temp_password_2025', 
    'owner', 
    '{"name": "Resto Bulla", "description": "Restored from chat history - 87 messages", "restored": true, "restoration_date": "2025-10-02"}',
    'general',
    'dynamic',
    'restaurant'
) ON CONFLICT (restaurant_id) DO NOTHING;

-- Restore bali-legal-consulting (11 messages)
INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
VALUES (
    'bali-legal-consulting', 
    'temp_password_2025', 
    'owner', 
    '{"name": "Bali Legal Consulting", "description": "Restored from chat history - 11 messages", "restored": true, "restoration_date": "2025-10-02"}',
    'legal',
    'dynamic',
    'consulting'
) ON CONFLICT (restaurant_id) DO NOTHING;

-- Restore bali_business_consulting (9 messages)
INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
VALUES (
    'bali_business_consulting', 
    'temp_password_2025', 
    'owner', 
    '{"name": "Bali Business Consulting", "description": "Restored from chat history - 9 messages", "restored": true, "restoration_date": "2025-10-02"}',
    'business',
    'dynamic',
    'consulting'
) ON CONFLICT (restaurant_id) DO NOTHING;

-- Ensure admin users exist
INSERT INTO restaurants (restaurant_id, password, role, data, restaurant_category, rag_mode, business_type)
VALUES 
    ('admin', 'admin123', 'admin', '{"name": "System Administrator"}', 'admin', 'dynamic', 'admin'),
    ('admin@admin.com', 'admin123', 'admin', '{"name": "Admin Email"}', 'admin', 'dynamic', 'admin')
ON CONFLICT (restaurant_id) DO NOTHING;

\echo ''
\echo '✅ RESTORATION COMPLETE! Final restaurant list:'
SELECT restaurant_id, role, data->>'name' as name, business_type, restaurant_category
FROM restaurants 
ORDER BY role, restaurant_id;

\echo ''
\echo '📊 SUMMARY:'
SELECT 
    COUNT(*) as total_restaurants,
    COUNT(*) FILTER (WHERE role = 'owner') as owner_restaurants,
    COUNT(*) FILTER (WHERE role = 'admin') as admin_users
FROM restaurants;
