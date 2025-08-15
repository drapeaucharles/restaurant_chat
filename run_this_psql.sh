#!/bin/bash

# Run this command to create the table:

PGPASSWORD=pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh psql -h shortline.proxy.rlwy.net -U postgres -p 31808 -d railway << 'EOF'
-- Fix transaction error first
ROLLBACK;

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
CREATE UNIQUE INDEX idx_menu_embeddings_unique ON menu_embeddings(restaurant_id, item_id);
CREATE INDEX idx_menu_embeddings_restaurant ON menu_embeddings(restaurant_id);

-- Verify it worked
SELECT 'Table created successfully!' as status;
\d menu_embeddings
EOF