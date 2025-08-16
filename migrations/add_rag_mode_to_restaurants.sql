-- Add RAG mode column to restaurants table
-- This allows each restaurant to choose their preferred AI chat mode

ALTER TABLE restaurants 
ADD COLUMN IF NOT EXISTS rag_mode VARCHAR(50) DEFAULT 'hybrid_smart_memory';

-- Set default values for existing restaurants
UPDATE restaurants 
SET rag_mode = 'hybrid_smart_memory' 
WHERE rag_mode IS NULL;

-- Add comment explaining the options
COMMENT ON COLUMN restaurants.rag_mode IS 'AI chat mode: optimized (fast/cheap), enhanced_v2 (quality), enhanced_v3 (memory), hybrid_smart (auto-routing), hybrid_smart_memory (auto-routing + memory)';