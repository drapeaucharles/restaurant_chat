-- Fix prices to match the original string format with dollar signs

\echo '💰 FIXING PRICES TO ORIGINAL STRING FORMAT...'
\echo ''

-- Update prices for bella_vista_restaurant with proper string format
UPDATE products SET price = 
CASE 
    WHEN category = 'Appetizers' THEN 
        CASE name
            WHEN 'Truffle Arancini' THEN 18.99
            WHEN 'Caprese Skewers' THEN 14.99
            WHEN 'Calamari Fritti' THEN 16.99
            WHEN 'Bruschetta Trio' THEN 15.99
            WHEN 'Stuffed Mushrooms' THEN 13.99
            WHEN 'Shrimp Cocktail' THEN 19.99
            WHEN 'Spinach Artichoke Dip' THEN 12.99
            WHEN 'Beef Carpaccio' THEN 18.99  -- Matches chat history
            WHEN 'Mezze Platter' THEN 17.99
            WHEN 'Oysters Rockefeller' THEN 19.99  -- Matches chat history
            ELSE 15.99
        END
    WHEN category = 'Main Courses' OR category = 'Mains' OR category = 'Pasta' THEN
        CASE name
            WHEN 'Spaghetti Carbonara' THEN 18.99  -- Matches chat history
            WHEN 'Seafood Linguine' THEN 32.99     -- Matches chat history
            WHEN 'Eggplant Parmigiana' THEN 18.99  -- Matches chat history
            WHEN 'Mushroom Wellington' THEN 22.99  -- Matches chat history
            WHEN 'Stuffed Bell Peppers' THEN 17.99 -- Matches chat history
            WHEN 'Vegetable Curry' THEN 16.99      -- Matches chat history
            WHEN 'Buddha Bowl' THEN 15.99          -- Matches chat history
            ELSE 24.99
        END
    WHEN category = 'Desserts' THEN 
        CASE name
            WHEN 'Tiramisu' THEN 8.95              -- Matches chat history
            WHEN 'Chocolate Lava Cake' THEN 10.99  -- Matches chat history
            ELSE 9.99
        END
    WHEN category = 'Salads' THEN 
        CASE name
            WHEN 'Caesar Salad' THEN 11.99         -- Matches chat history
            ELSE 13.99
        END
    WHEN category = 'Beverages' OR category = 'Drinks' THEN 7.99
    WHEN category = 'Soups' THEN 8.99
    ELSE 19.99
END
WHERE business_id = 'bella_vista_restaurant';

-- Update other restaurants with reasonable prices
UPDATE products SET price = 
CASE 
    WHEN category = 'Appetizers' THEN 11.99
    WHEN category = 'Main Courses' OR category = 'Mains' THEN 19.99
    WHEN category = 'Desserts' THEN 8.99
    WHEN category = 'Beverages' OR category = 'Drinks' THEN 5.99
    WHEN category = 'Salads' THEN 12.99
    WHEN category = 'Soups' THEN 7.99
    ELSE 16.99
END
WHERE business_id = 'RestoBulla';

-- Update consulting services (hourly rates)
UPDATE products SET price = 
CASE 
    WHEN name ILIKE '%consultation%' OR name ILIKE '%advice%' THEN 150.00
    WHEN name ILIKE '%legal%' OR name ILIKE '%contract%' THEN 200.00
    WHEN name ILIKE '%business%' OR name ILIKE '%strategy%' THEN 175.00
    WHEN name ILIKE '%document%' OR name ILIKE '%filing%' THEN 100.00
    ELSE 125.00
END
WHERE business_id IN ('bali-legal-consulting', 'bali_business_consulting');

\echo '✅ Prices updated! Now re-migrating with proper price format...'

-- Re-migrate with updated prices and proper string format for bella_vista_restaurant
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
                'dish', name,
                'item_description', description,
                'description', description,
                'price', '$' || price::text,  -- Convert to string with $ prefix
                'category', category,
                'subcategory', category,
                'ingredients', COALESCE(features->'ingredients', '[]'::jsonb),
                'allergens', COALESCE(requirements->'allergens', '[]'::jsonb),
                'dietary_tags', COALESCE(tags->'dietary', '[]'::jsonb),
                'is_vegetarian', COALESCE((tags->'dietary' ? 'vegetarian')::boolean, false),
                'is_vegan', COALESCE((tags->'dietary' ? 'vegan')::boolean, false),
                'is_gluten_free', COALESCE((tags->'dietary' ? 'gluten-free')::boolean, false),
                'is_nut_free', COALESCE((tags->'dietary' ? 'nut-free')::boolean, true),
                'is_dairy_free', COALESCE((tags->'dietary' ? 'dairy-free')::boolean, false),
                'available', COALESCE(available, true),
                'image_url', image_url
            )
        )
        FROM products 
        WHERE business_id = 'bella_vista_restaurant'
    )
)
WHERE restaurant_id = 'bella_vista_restaurant';

-- Re-migrate for other restaurants
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
                'dish', name,
                'item_description', description,
                'description', description,
                'price', '$' || price::text,
                'category', category,
                'subcategory', category,
                'ingredients', COALESCE(features->'ingredients', '[]'::jsonb),
                'allergens', COALESCE(requirements->'allergens', '[]'::jsonb),
                'dietary_tags', COALESCE(tags->'dietary', '[]'::jsonb),
                'is_vegetarian', COALESCE((tags->'dietary' ? 'vegetarian')::boolean, false),
                'is_vegan', COALESCE((tags->'dietary' ? 'vegan')::boolean, false),
                'is_gluten_free', COALESCE((tags->'dietary' ? 'gluten-free')::boolean, false),
                'is_nut_free', COALESCE((tags->'dietary' ? 'nut-free')::boolean, true),
                'is_dairy_free', COALESCE((tags->'dietary' ? 'dairy-free')::boolean, false),
                'available', COALESCE(available, true),
                'image_url', image_url
            )
        )
        FROM products 
        WHERE business_id = restaurants.restaurant_id
    )
)
WHERE restaurant_id IN ('RestoBulla', 'bali-legal-consulting', 'bali_business_consulting');

\echo ''
\echo '💰 PRICE FIX COMPLETE! Sample with proper format:'

-- Show sample menu items with proper price format
SELECT 
    menu_item->>'title' as dish_name,
    menu_item->>'price' as price,
    menu_item->>'category' as category
FROM restaurants,
     json_array_elements(data->'menu') as menu_item
WHERE restaurant_id = 'bella_vista_restaurant'
AND menu_item->>'title' IN ('Beef Carpaccio', 'Spaghetti Carbonara', 'Caesar Salad', 'Tiramisu', 'Oysters Rockefeller')
ORDER BY menu_item->>'category', menu_item->>'title';
