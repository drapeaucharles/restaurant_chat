-- Fix menu structure to match what the AI code expects

\echo '🔧 FIXING MENU STRUCTURE TO MATCH AI CODE EXPECTATIONS...'
\echo ''

-- Update bella_vista_restaurant menu with correct field names
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
                'dish', p.name,  -- AI code looks for 'dish' field
                'item_description', p.description,
                'description', p.description,
                'price', '$' || p.price::text,
                'category', p.category,
                'subcategory', p.category,
                -- CRITICAL: AI code looks for these specific fields
                'restaurant_category', p.category,  -- Single category field
                'restaurant_categories', ARRAY[p.category],  -- Array of categories
                -- Add realistic ingredients based on dish names
                'ingredients', 
                CASE 
                    WHEN p.name ILIKE '%truffle%arancini%' THEN ARRAY['Arborio rice', 'Truffle oil', 'Parmesan cheese', 'Breadcrumbs', 'Eggs', 'Marinara sauce']
                    WHEN p.name ILIKE '%caprese%' THEN ARRAY['Fresh mozzarella', 'Cherry tomatoes', 'Fresh basil', 'Balsamic glaze', 'Olive oil']
                    WHEN p.name ILIKE '%calamari%' THEN ARRAY['Squid rings', 'Flour', 'Eggs', 'Breadcrumbs', 'Lemon', 'Spicy aioli']
                    WHEN p.name ILIKE '%bruschetta%' THEN ARRAY['Bread', 'Tomatoes', 'Garlic', 'Basil', 'Olive oil', 'Mushrooms', 'Goat cheese', 'Olives']
                    WHEN p.name ILIKE '%beef%carpaccio%' THEN ARRAY['Raw beef', 'Arugula', 'Capers', 'Parmesan cheese', 'Lemon', 'Olive oil']
                    WHEN p.name ILIKE '%spaghetti%carbonara%' THEN ARRAY['Spaghetti', 'Guanciale', 'Egg yolk', 'Parmesan cheese', 'Black pepper']
                    WHEN p.name ILIKE '%seafood%linguine%' THEN ARRAY['Linguine', 'Shrimp', 'Scallops', 'Mussels', 'White wine', 'Garlic', 'Olive oil']
                    WHEN p.name ILIKE '%caesar%salad%' THEN ARRAY['Romaine lettuce', 'Parmesan cheese', 'Croutons', 'Caesar dressing', 'Anchovies']
                    WHEN p.name ILIKE '%tiramisu%' THEN ARRAY['Ladyfingers', 'Mascarpone', 'Espresso', 'Marsala wine', 'Cocoa powder', 'Eggs']
                    WHEN p.name ILIKE '%chocolate%lava%' THEN ARRAY['Dark chocolate', 'Butter', 'Eggs', 'Sugar', 'Flour', 'Vanilla ice cream']
                    WHEN p.name ILIKE '%oysters%rockefeller%' THEN ARRAY['Fresh oysters', 'Spinach', 'Herbs', 'Hollandaise sauce', 'Butter']
                    WHEN p.name ILIKE '%lobster%ravioli%' THEN ARRAY['Fresh pasta', 'Lobster meat', 'Garlic', 'Butter', 'Parsley', 'White wine']
                    ELSE ARRAY['Various ingredients']
                END,
                -- Add realistic allergens (as array, not JSON)
                'allergens',
                CASE 
                    WHEN p.name ILIKE '%truffle%arancini%' THEN ARRAY['Dairy', 'Gluten', 'Eggs']  -- Has parmesan, breadcrumbs, eggs
                    WHEN p.name ILIKE '%caprese%' THEN ARRAY['Dairy']  -- Has mozzarella
                    WHEN p.name ILIKE '%calamari%' THEN ARRAY['Shellfish', 'Gluten', 'Eggs']  -- Squid, flour, eggs
                    WHEN p.name ILIKE '%bruschetta%' THEN ARRAY['Gluten', 'Dairy']  -- Bread, goat cheese
                    WHEN p.name ILIKE '%beef%carpaccio%' THEN ARRAY['Dairy']  -- Has parmesan
                    WHEN p.name ILIKE '%spaghetti%carbonara%' THEN ARRAY['Gluten', 'Eggs', 'Dairy']  -- Pasta, eggs, cheese
                    WHEN p.name ILIKE '%seafood%linguine%' THEN ARRAY['Shellfish', 'Gluten']  -- Shellfish, pasta
                    WHEN p.name ILIKE '%caesar%salad%' THEN ARRAY['Fish', 'Dairy', 'Gluten']  -- Anchovies, cheese, croutons
                    WHEN p.name ILIKE '%tiramisu%' THEN ARRAY['Eggs', 'Dairy', 'Gluten']  -- Eggs, mascarpone, ladyfingers
                    WHEN p.name ILIKE '%chocolate%lava%' THEN ARRAY['Eggs', 'Dairy', 'Gluten']  -- Eggs, butter, flour
                    WHEN p.name ILIKE '%oysters%rockefeller%' THEN ARRAY['Shellfish', 'Dairy', 'Eggs']  -- Oysters, butter, hollandaise
                    WHEN p.name ILIKE '%lobster%ravioli%' THEN ARRAY['Shellfish', 'Gluten', 'Eggs']  -- Lobster, pasta, eggs
                    WHEN p.name ILIKE '%cheese%' OR p.name ILIKE '%parmesan%' OR p.name ILIKE '%mozzarella%' THEN ARRAY['Dairy']
                    WHEN p.name ILIKE '%pasta%' OR p.name ILIKE '%spaghetti%' OR p.name ILIKE '%linguine%' THEN ARRAY['Gluten', 'Eggs']
                    WHEN p.name ILIKE '%seafood%' OR p.name ILIKE '%shrimp%' OR p.name ILIKE '%scallops%' OR p.name ILIKE '%mussels%' THEN ARRAY['Shellfish']
                    ELSE ARRAY[]::text[]
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

\echo '✅ Fixed menu structure for bella_vista_restaurant!'

\echo ''
\echo '🔍 VERIFICATION - Sample fixed menu item:'

-- Show fixed menu item with correct structure
SELECT 
    menu_item->>'dish' as dish_name,
    menu_item->>'price' as price,
    menu_item->>'restaurant_category' as category,
    menu_item->'restaurant_categories' as categories_array,
    menu_item->'ingredients' as ingredients,
    menu_item->'allergens' as allergens,
    menu_item->>'is_vegetarian' as vegetarian
FROM restaurants,
     json_array_elements(data->'menu') as menu_item
WHERE restaurant_id = 'bella_vista_restaurant'
AND menu_item->>'dish' = 'Truffle Arancini';
