-- Migration to add photo_url support to menu items
-- Since menu items are stored in JSON within the Restaurant.data column,
-- no database schema changes are needed.
-- 
-- The photo_url field is added to the MenuItem schema and will be stored
-- as part of the JSON data structure.
--
-- This file is for documentation purposes only.
-- No SQL commands need to be executed.

-- If you had a separate menu_items table, you would use:
-- ALTER TABLE menu_items ADD COLUMN photo_url VARCHAR(255);

-- But since we're using JSON storage in the Restaurant.data column,
-- the photo_url is automatically supported through the JSON structure.