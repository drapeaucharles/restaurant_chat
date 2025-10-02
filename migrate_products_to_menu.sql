-- Migrate products table data into restaurant data.menu field
-- This will make the chat system work by putting menu items where it expects them

\echo '🔧 MIGRATING PRODUCTS TO RESTAURANT MENU DATA...'
\echo ''

-- First, let's see what we're working with
\echo '📊 Current products by restaurant:'
SELECT business_id, COUNT(*) as product_count
FROM products 
GROUP BY business_id 
ORDER BY product_count DESC;

\echo ''
\echo '🔧 MIGRATING bella_vista_restaurant products to menu...'

-- Update bella_vista_restaurant with menu data from products
UPDATE restaurants 
SET data = jsonb_set(
    data::jsonb, 
    '{menu}', 
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', id,
                'title', name,
                'name', name,
                'item_description', description,
                'description', description,
                'price', COALESCE(price, 0),
                'category', category,
                'subcategory', category,
                'ingredients', COALESCE(features->'ingredients', '[]'::jsonb),
                'allergens', COALESCE(requirements->'allergens', '[]'::jsonb),
                'dietary_tags', COALESCE(tags->'dietary', '[]'::jsonb),
                'available', COALESCE(available, true),
                'image_url', image_url
            )
        )
        FROM products 
        WHERE business_id = 'bella_vista_restaurant'
    )
)
WHERE restaurant_id = 'bella_vista_restaurant';

\echo '🔧 MIGRATING RestoBulla products to menu...'

-- Update RestoBulla with menu data from products
UPDATE restaurants 
SET data = jsonb_set(
    data::jsonb, 
    '{menu}', 
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', id,
                'title', name,
                'name', name,
                'item_description', description,
                'description', description,
                'price', COALESCE(price, 0),
                'category', category,
                'subcategory', category,
                'ingredients', COALESCE(features->'ingredients', '[]'::jsonb),
                'allergens', COALESCE(requirements->'allergens', '[]'::jsonb),
                'dietary_tags', COALESCE(tags->'dietary', '[]'::jsonb),
                'available', COALESCE(available, true),
                'image_url', image_url
            )
        )
        FROM products 
        WHERE business_id = 'RestoBulla'
    )
)
WHERE restaurant_id = 'RestoBulla';

\echo '🔧 MIGRATING bali-legal-consulting products to menu...'

-- Update bali-legal-consulting with menu data from products
UPDATE restaurants 
SET data = jsonb_set(
    data::jsonb, 
    '{menu}', 
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', id,
                'title', name,
                'name', name,
                'item_description', description,
                'description', description,
                'price', COALESCE(price, 0),
                'category', category,
                'subcategory', category,
                'ingredients', COALESCE(features->'ingredients', '[]'::jsonb),
                'allergens', COALESCE(requirements->'allergens', '[]'::jsonb),
                'dietary_tags', COALESCE(tags->'dietary', '[]'::jsonb),
                'available', COALESCE(available, true),
                'image_url', image_url
            )
        )
        FROM products 
        WHERE business_id = 'bali-legal-consulting'
    )
)
WHERE restaurant_id = 'bali-legal-consulting';

\echo '🔧 MIGRATING bali_business_consulting products to menu...'

-- Update bali_business_consulting with menu data from products
UPDATE restaurants 
SET data = jsonb_set(
    data::jsonb, 
    '{menu}', 
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', id,
                'title', name,
                'name', name,
                'item_description', description,
                'description', description,
                'price', COALESCE(price, 0),
                'category', category,
                'subcategory', category,
                'ingredients', COALESCE(features->'ingredients', '[]'::jsonb),
                'allergens', COALESCE(requirements->'allergens', '[]'::jsonb),
                'dietary_tags', COALESCE(tags->'dietary', '[]'::jsonb),
                'available', COALESCE(available, true),
                'image_url', image_url
            )
        )
        FROM products 
        WHERE business_id = 'bali_business_consulting'
    )
)
WHERE restaurant_id = 'bali_business_consulting';

\echo ''
\echo '✅ MIGRATION COMPLETE! Verifying results...'

-- Verify the migration worked
SELECT 
    restaurant_id,
    data->>'name' as restaurant_name,
    jsonb_array_length(COALESCE(data->'menu', '[]'::jsonb)) as menu_items_count
FROM restaurants 
WHERE role = 'owner'
ORDER BY restaurant_id;

\echo ''
\echo '🔍 Sample menu items for bella_vista_restaurant:'
SELECT 
    menu_item->>'title' as dish_name,
    menu_item->>'price' as price,
    menu_item->>'category' as category
FROM restaurants,
     jsonb_array_elements(data->'menu') as menu_item
WHERE restaurant_id = 'bella_vista_restaurant'
LIMIT 5;
