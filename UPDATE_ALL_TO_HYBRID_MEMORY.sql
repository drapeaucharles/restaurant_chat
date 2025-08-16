-- Update all restaurants to use the new hybrid_smart_memory mode
-- This gives all restaurants the best AI experience with smart routing + memory

-- First, ensure the column exists
ALTER TABLE restaurants 
ADD COLUMN IF NOT EXISTS rag_mode VARCHAR(50) DEFAULT 'hybrid_smart_memory';

-- Update ALL existing restaurants to the new mode
UPDATE restaurants 
SET rag_mode = 'hybrid_smart_memory';

-- Show the results
SELECT 
    restaurant_id, 
    data->>'name' as restaurant_name,
    rag_mode 
FROM restaurants 
ORDER BY restaurant_id;

-- Add comment explaining the mode
COMMENT ON COLUMN restaurants.rag_mode IS 'AI chat mode: optimized (fast/cheap), enhanced_v2 (quality), enhanced_v3 (memory), hybrid_smart (auto-routing), hybrid_smart_memory (auto-routing + memory - RECOMMENDED)';