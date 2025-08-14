-- Manual pgvector setup for Railway PostgreSQL
-- Run this if automatic migration fails

-- 1. Enable pgvector extension (requires superuser)
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Create menu embeddings table
CREATE TABLE IF NOT EXISTS menu_embeddings (
    id SERIAL PRIMARY KEY,
    restaurant_id VARCHAR(255) NOT NULL,
    item_id VARCHAR(255) NOT NULL,
    item_name TEXT NOT NULL,
    item_description TEXT,
    item_price VARCHAR(50),
    item_category VARCHAR(100),
    item_ingredients TEXT[],
    dietary_tags TEXT[],
    full_text TEXT NOT NULL,
    embedding vector(384),  -- 384 dimensions for all-MiniLM-L6-v2
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(restaurant_id, item_id)
);

-- 3. Create vector similarity search index
CREATE INDEX IF NOT EXISTS menu_embeddings_embedding_idx 
ON menu_embeddings 
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 4. Create restaurant_id index for filtering
CREATE INDEX IF NOT EXISTS menu_embeddings_restaurant_idx 
ON menu_embeddings(restaurant_id);

-- 5. Verify setup
SELECT 
    EXISTS (
        SELECT 1 
        FROM pg_extension 
        WHERE extname = 'vector'
    ) as vector_extension_installed,
    EXISTS (
        SELECT 1 
        FROM information_schema.tables 
        WHERE table_name = 'menu_embeddings'
    ) as embeddings_table_created;