-- EXECUTE THESE COMMANDS IN YOUR DATABASE TO DELETE THE DUMMY RESTAURANTS

-- 1. Delete Test restaurant and its data
DELETE FROM menu_embeddings WHERE restaurant_id = 'Test';
DELETE FROM chat_messages WHERE restaurant_id = 'Test';
DELETE FROM clients WHERE restaurant_id = 'Test';
DELETE FROM restaurants WHERE restaurant_id = 'Test';

-- 2. Delete RestoLorenzo (Lorenzo Papa) and its data
DELETE FROM menu_embeddings WHERE restaurant_id = 'RestoLorenzo';
DELETE FROM chat_messages WHERE restaurant_id = 'RestoLorenzo';
DELETE FROM clients WHERE restaurant_id = 'RestoLorenzo';
DELETE FROM restaurants WHERE restaurant_id = 'RestoLorenzo';

-- 3. Verify they're gone
SELECT restaurant_id, data->>'name' as name 
FROM restaurants 
ORDER BY restaurant_id;

-- Should only show:
-- admin@admin.com | System Admin
-- RestoBulla | Bulla Gastrobar Tampa
-- bella_vista_restaurant | Bella Vista Gourmet