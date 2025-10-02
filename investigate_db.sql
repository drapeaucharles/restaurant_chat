-- Database Investigation Script
-- Check current state of the database

\echo '🔍 INVESTIGATING DATABASE STATE...'
\echo ''

-- Check what tables exist
\echo '📋 EXISTING TABLES:'
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
ORDER BY table_name;

\echo ''
\echo '🏪 RESTAURANTS TABLE ANALYSIS:'

-- Check if restaurants table exists and its structure
SELECT column_name, data_type, is_nullable 
FROM information_schema.columns 
WHERE table_name = 'restaurants'
ORDER BY ordinal_position;

\echo ''
\echo '📊 CURRENT RESTAURANTS:'

-- Get current restaurant data
SELECT restaurant_id, role, 
       COALESCE(data->>'name', 'No name') as name,
       restaurant_category,
       business_type,
       created_at
FROM restaurants 
ORDER BY role, restaurant_id;

\echo ''
\echo '🏢 BUSINESSES TABLE (if exists):'

-- Check businesses table
SELECT business_id, type, name, role, created_at
FROM businesses 
ORDER BY type, business_id;

\echo ''
\echo '💬 RESTAURANTS WITH CHAT ACTIVITY:'

-- Find restaurants that have chat messages
SELECT DISTINCT restaurant_id, COUNT(*) as message_count,
       MAX(created_at) as last_message
FROM chat_messages 
GROUP BY restaurant_id 
ORDER BY message_count DESC
LIMIT 20;

\echo ''
\echo '🍽️ RESTAURANTS WITH MENU DATA:'

-- Find restaurants that have menu items
SELECT DISTINCT restaurant_id, COUNT(*) as item_count
FROM menu_items 
GROUP BY restaurant_id 
ORDER BY item_count DESC;

\echo ''
\echo '❌ MISSING RESTAURANTS (have chat but no restaurant record):'

-- Find restaurant IDs in chat but not in restaurants table
SELECT DISTINCT cm.restaurant_id, COUNT(*) as message_count
FROM chat_messages cm
LEFT JOIN restaurants r ON cm.restaurant_id = r.restaurant_id
WHERE r.restaurant_id IS NULL
  AND cm.restaurant_id NOT IN ('admin', 'admin@admin.com')
GROUP BY cm.restaurant_id
ORDER BY message_count DESC;
