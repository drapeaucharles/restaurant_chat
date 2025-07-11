-- Add restaurant_categories column to restaurants table
ALTER TABLE restaurants ADD COLUMN IF NOT EXISTS restaurant_categories JSON DEFAULT '[]';