-- Check menu/product data for restaurants

\echo '🍽️ CHECKING MENU/PRODUCT DATA...'
\echo ''

\echo 'Tables that might contain menu data:'
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND (table_name LIKE '%menu%' OR table_name LIKE '%product%' OR table_name LIKE '%item%')
ORDER BY table_name;

\echo ''
\echo '📊 Products table data:'
SELECT restaurant_id, COUNT(*) as product_count
FROM products 
GROUP BY restaurant_id 
ORDER BY product_count DESC;

\echo ''
\echo '🔍 Sample products for bella_vista_restaurant:'
SELECT name, price, category, subcategory, description
FROM products 
WHERE restaurant_id = 'bella_vista_restaurant'
LIMIT 10;

\echo ''
\echo '📋 Restaurant data (checking for embedded menu):'
SELECT restaurant_id, 
       CASE 
           WHEN data ? 'menu' THEN 'Has menu in data'
           ELSE 'No menu in data'
       END as menu_status,
       jsonb_array_length(COALESCE(data->'menu', '[]'::jsonb)) as menu_items_count
FROM restaurants 
WHERE role = 'owner'
ORDER BY restaurant_id;
