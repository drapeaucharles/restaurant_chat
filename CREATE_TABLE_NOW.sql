-- RAG Table Creation Script
-- Run this directly on your Railway PostgreSQL

-- Drop existing table if any
DROP TABLE IF EXISTS menu_embeddings CASCADE;

-- Create the table
CREATE TABLE menu_embeddings (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) NOT NULL,
    item_name VARCHAR(255) NOT NULL,
    item_description TEXT,
    item_price VARCHAR(50),
    item_category VARCHAR(100),
    item_ingredients TEXT,
    dietary_tags TEXT,
    full_text TEXT NOT NULL,
    embedding_json TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE UNIQUE INDEX idx_menu_embeddings_unique 
ON menu_embeddings(restaurant_id, item_id);

CREATE INDEX idx_menu_embeddings_restaurant 
ON menu_embeddings(restaurant_id);

-- Verify table was created
SELECT 'Table created successfully!' as message,
       COUNT(*) as column_count
FROM information_schema.columns 
WHERE table_name = 'menu_embeddings';

-- Show table structure
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'menu_embeddings'
ORDER BY ordinal_position;