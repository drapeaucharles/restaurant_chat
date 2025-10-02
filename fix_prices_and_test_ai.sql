-- Fix prices for menu items and prepare for AI testing

\echo '💰 FIXING MENU PRICES...'
\echo ''

-- Update prices for bella_vista_restaurant (Italian restaurant)
UPDATE products SET price = 
CASE 
    WHEN category = 'Appetizers' THEN 
        CASE name
            WHEN 'Truffle Arancini' THEN 18.00
            WHEN 'Caprese Skewers' THEN 14.00
            WHEN 'Calamari Fritti' THEN 16.00
            WHEN 'Bruschetta Trio' THEN 15.00
            WHEN 'Stuffed Mushrooms' THEN 13.00
            WHEN 'Shrimp Cocktail' THEN 19.00
            WHEN 'Spinach Artichoke Dip' THEN 12.00
            WHEN 'Beef Carpaccio' THEN 22.00
            WHEN 'Mezze Platter' THEN 17.00
            WHEN 'Oysters Rockefeller' THEN 24.00
            ELSE 15.00
        END
    WHEN category = 'Main Courses' OR category = 'Mains' THEN
        CASE 
            WHEN name ILIKE '%lobster%' OR name ILIKE '%ribeye%' THEN 45.00
            WHEN name ILIKE '%salmon%' OR name ILIKE '%lamb%' THEN 32.00
            WHEN name ILIKE '%chicken%' OR name ILIKE '%pasta%' THEN 24.00
            WHEN name ILIKE '%pizza%' THEN 18.00
            ELSE 28.00
        END
    WHEN category = 'Desserts' THEN 12.00
    WHEN category = 'Beverages' OR category = 'Drinks' THEN 8.00
    WHEN category = 'Salads' THEN 16.00
    WHEN category = 'Soups' THEN 11.00
    ELSE 20.00
END
WHERE business_id = 'bella_vista_restaurant' AND price = 0;

-- Update prices for RestoBulla
UPDATE products SET price = 
CASE 
    WHEN category = 'Appetizers' THEN 12.00
    WHEN category = 'Main Courses' OR category = 'Mains' THEN 22.00
    WHEN category = 'Desserts' THEN 9.00
    WHEN category = 'Beverages' OR category = 'Drinks' THEN 6.00
    WHEN category = 'Salads' THEN 14.00
    WHEN category = 'Soups' THEN 8.00
    ELSE 18.00
END
WHERE business_id = 'RestoBulla' AND price = 0;

-- Update prices for consulting services (hourly rates)
UPDATE products SET price = 
CASE 
    WHEN name ILIKE '%consultation%' OR name ILIKE '%advice%' THEN 150.00
    WHEN name ILIKE '%legal%' OR name ILIKE '%contract%' THEN 200.00
    WHEN name ILIKE '%business%' OR name ILIKE '%strategy%' THEN 175.00
    WHEN name ILIKE '%document%' OR name ILIKE '%filing%' THEN 100.00
    ELSE 125.00
END
WHERE business_id IN ('bali-legal-consulting', 'bali_business_consulting') AND price = 0;

\echo '✅ Prices updated! Now re-migrating to restaurant menu data...'

-- Re-migrate with updated prices for bella_vista_restaurant
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
                'price', price,
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

-- Re-migrate for RestoBulla
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
                'price', price,
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

\echo ''
\echo '💰 PRICE FIX COMPLETE! Sample with new prices:'

-- Show sample menu items with updated prices
SELECT 
    menu_item->>'title' as dish_name,
    menu_item->>'price' as price,
    menu_item->>'category' as category
FROM restaurants,
     json_array_elements(data->'menu') as menu_item
WHERE restaurant_id = 'bella_vista_restaurant'
ORDER BY (menu_item->>'price')::numeric DESC
LIMIT 8;
