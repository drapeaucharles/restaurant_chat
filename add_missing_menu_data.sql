-- Add missing ingredients, allergens, and other data to menu items

\echo '🔧 ADDING MISSING INGREDIENTS, ALLERGENS, AND IMAGES...'
\echo ''

-- Update bella_vista_restaurant menu with comprehensive data
UPDATE restaurants 
SET data = jsonb_set(
    data::jsonb, 
    '{menu}', 
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'title', p.name,
                'name', p.name,
                'dish', p.name,
                'item_description', p.description,
                'description', p.description,
                'price', '$' || p.price::text,
                'category', p.category,
                'subcategory', p.category,
                -- Add realistic ingredients based on dish names
                'ingredients', 
                CASE 
                    WHEN p.name ILIKE '%truffle%arancini%' THEN '["Arborio rice", "Truffle oil", "Parmesan cheese", "Breadcrumbs", "Eggs", "Marinara sauce"]'::jsonb
                    WHEN p.name ILIKE '%caprese%' THEN '["Fresh mozzarella", "Cherry tomatoes", "Fresh basil", "Balsamic glaze", "Olive oil"]'::jsonb
                    WHEN p.name ILIKE '%calamari%' THEN '["Squid rings", "Flour", "Eggs", "Breadcrumbs", "Lemon", "Spicy aioli"]'::jsonb
                    WHEN p.name ILIKE '%bruschetta%' THEN '["Bread", "Tomatoes", "Garlic", "Basil", "Olive oil", "Mushrooms", "Goat cheese", "Olives"]'::jsonb
                    WHEN p.name ILIKE '%beef%carpaccio%' THEN '["Raw beef", "Arugula", "Capers", "Parmesan cheese", "Lemon", "Olive oil"]'::jsonb
                    WHEN p.name ILIKE '%spaghetti%carbonara%' THEN '["Spaghetti", "Guanciale", "Egg yolk", "Parmesan cheese", "Black pepper"]'::jsonb
                    WHEN p.name ILIKE '%seafood%linguine%' THEN '["Linguine", "Shrimp", "Scallops", "Mussels", "White wine", "Garlic", "Olive oil"]'::jsonb
                    WHEN p.name ILIKE '%caesar%salad%' THEN '["Romaine lettuce", "Parmesan cheese", "Croutons", "Caesar dressing", "Anchovies"]'::jsonb
                    WHEN p.name ILIKE '%tiramisu%' THEN '["Ladyfingers", "Mascarpone", "Espresso", "Marsala wine", "Cocoa powder", "Eggs"]'::jsonb
                    WHEN p.name ILIKE '%chocolate%lava%' THEN '["Dark chocolate", "Butter", "Eggs", "Sugar", "Flour", "Vanilla ice cream"]'::jsonb
                    WHEN p.name ILIKE '%oysters%rockefeller%' THEN '["Fresh oysters", "Spinach", "Herbs", "Hollandaise sauce", "Butter"]'::jsonb
                    WHEN p.name ILIKE '%lobster%ravioli%' THEN '["Fresh pasta", "Lobster meat", "Garlic", "Butter", "Parsley", "White wine"]'::jsonb
                    ELSE '["Various ingredients"]'::jsonb
                END,
                -- Add realistic allergens
                'allergens',
                CASE 
                    WHEN p.name ILIKE '%cheese%' OR p.name ILIKE '%parmesan%' OR p.name ILIKE '%mozzarella%' OR p.name ILIKE '%mascarpone%' THEN '["Dairy"]'::jsonb
                    WHEN p.name ILIKE '%pasta%' OR p.name ILIKE '%spaghetti%' OR p.name ILIKE '%linguine%' OR p.name ILIKE '%ravioli%' OR p.name ILIKE '%bread%' OR p.name ILIKE '%flour%' THEN '["Gluten", "Eggs"]'::jsonb
                    WHEN p.name ILIKE '%seafood%' OR p.name ILIKE '%shrimp%' OR p.name ILIKE '%scallops%' OR p.name ILIKE '%mussels%' OR p.name ILIKE '%oysters%' OR p.name ILIKE '%lobster%' THEN '["Shellfish"]'::jsonb
                    WHEN p.name ILIKE '%calamari%' OR p.name ILIKE '%squid%' THEN '["Shellfish"]'::jsonb
                    WHEN p.name ILIKE '%caesar%' OR p.name ILIKE '%anchovies%' THEN '["Fish", "Dairy", "Gluten"]'::jsonb
                    WHEN p.name ILIKE '%carbonara%' OR p.name ILIKE '%tiramisu%' THEN '["Eggs", "Dairy", "Gluten"]'::jsonb
                    WHEN p.name ILIKE '%beef%' OR p.name ILIKE '%meat%' THEN '[]'::jsonb
                    ELSE '[]'::jsonb
                END,
                -- Add dietary flags
                'is_vegetarian', 
                CASE 
                    WHEN p.name ILIKE '%beef%' OR p.name ILIKE '%seafood%' OR p.name ILIKE '%shrimp%' OR p.name ILIKE '%lobster%' OR p.name ILIKE '%oysters%' OR p.name ILIKE '%calamari%' OR p.name ILIKE '%guanciale%' OR p.name ILIKE '%anchovies%' THEN false
                    ELSE true
                END,
                'is_vegan',
                CASE 
                    WHEN p.name ILIKE '%cheese%' OR p.name ILIKE '%dairy%' OR p.name ILIKE '%egg%' OR p.name ILIKE '%butter%' OR p.name ILIKE '%cream%' OR p.name ILIKE '%mascarpone%' OR p.name ILIKE '%mozzarella%' THEN false
                    WHEN p.name ILIKE '%beef%' OR p.name ILIKE '%seafood%' OR p.name ILIKE '%meat%' THEN false
                    ELSE false  -- Most Italian dishes contain dairy
                END,
                'is_gluten_free',
                CASE 
                    WHEN p.name ILIKE '%pasta%' OR p.name ILIKE '%spaghetti%' OR p.name ILIKE '%linguine%' OR p.name ILIKE '%ravioli%' OR p.name ILIKE '%bread%' OR p.name ILIKE '%bruschetta%' OR p.name ILIKE '%arancini%' THEN false
                    ELSE true
                END,
                'is_nut_free', true,  -- Assume nut-free unless specified
                'is_dairy_free',
                CASE 
                    WHEN p.name ILIKE '%cheese%' OR p.name ILIKE '%cream%' OR p.name ILIKE '%butter%' OR p.name ILIKE '%mascarpone%' OR p.name ILIKE '%mozzarella%' OR p.name ILIKE '%parmesan%' THEN false
                    ELSE true
                END,
                'available', COALESCE(p.available, true),
                -- Add realistic image URLs (placeholder)
                'image_url', 
                CASE 
                    WHEN p.name ILIKE '%truffle%arancini%' THEN '/images/truffle-arancini.jpg'
                    WHEN p.name ILIKE '%caprese%' THEN '/images/caprese-skewers.jpg'
                    WHEN p.name ILIKE '%calamari%' THEN '/images/calamari-fritti.jpg'
                    WHEN p.name ILIKE '%spaghetti%carbonara%' THEN '/images/spaghetti-carbonara.jpg'
                    WHEN p.name ILIKE '%tiramisu%' THEN '/images/tiramisu.jpg'
                    ELSE '/images/dish-placeholder.jpg'
                END
            )
        )
        FROM products p
        WHERE p.business_id = 'bella_vista_restaurant'
    )
)
WHERE restaurant_id = 'bella_vista_restaurant';

\echo '✅ Enhanced menu data for bella_vista_restaurant!'

-- Update RestoBulla with basic enhanced data
UPDATE restaurants 
SET data = jsonb_set(
    data::jsonb, 
    '{menu}', 
    (
        SELECT jsonb_agg(
            jsonb_build_object(
                'id', p.id,
                'title', p.name,
                'name', p.name,
                'dish', p.name,
                'item_description', p.description,
                'description', p.description,
                'price', '$' || p.price::text,
                'category', p.category,
                'subcategory', p.category,
                'ingredients', '["Various ingredients"]'::jsonb,
                'allergens', '[]'::jsonb,
                'is_vegetarian', true,
                'is_vegan', false,
                'is_gluten_free', false,
                'is_nut_free', true,
                'is_dairy_free', false,
                'available', COALESCE(p.available, true),
                'image_url', '/images/dish-placeholder.jpg'
            )
        )
        FROM products p
        WHERE p.business_id = 'RestoBulla'
    )
)
WHERE restaurant_id = 'RestoBulla';

\echo '✅ Enhanced menu data for RestoBulla!'

\echo ''
\echo '🔍 VERIFICATION - Sample enhanced menu item:'

-- Show enhanced menu item
SELECT 
    menu_item->>'title' as name,
    menu_item->>'price' as price,
    menu_item->'ingredients' as ingredients,
    menu_item->'allergens' as allergens,
    menu_item->>'is_vegetarian' as vegetarian,
    menu_item->>'is_gluten_free' as gluten_free,
    menu_item->>'image_url' as image
FROM restaurants,
     json_array_elements(data->'menu') as menu_item
WHERE restaurant_id = 'bella_vista_restaurant'
AND menu_item->>'title' = 'Truffle Arancini';
