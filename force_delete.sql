-- SQL commands to delete dummy restaurants
-- Run these in your database

-- First check what we're deleting
SELECT restaurant_id, data->>'name' as name, role 
FROM restaurants 
WHERE restaurant_id IN ('Test', 'RestoLorenzo');

-- Delete related data first (foreign key constraints)
DELETE FROM menu_embeddings WHERE restaurant_id IN ('Test', 'RestoLorenzo');
DELETE FROM chat_messages WHERE restaurant_id IN ('Test', 'RestoLorenzo');
DELETE FROM clients WHERE restaurant_id IN ('Test', 'RestoLorenzo');

-- Finally delete the restaurants
DELETE FROM restaurants WHERE restaurant_id IN ('Test', 'RestoLorenzo');

-- Verify final state
SELECT restaurant_id, data->>'name' as name, role 
FROM restaurants
ORDER BY restaurant_id;