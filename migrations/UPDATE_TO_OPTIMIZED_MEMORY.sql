-- Update all restaurants to use optimized_with_memory RAG mode
UPDATE restaurants 
SET rag_mode = 'optimized_with_memory'
WHERE rag_mode IS NOT NULL;

-- Show verification
SELECT rag_mode, COUNT(*) as restaurant_count
FROM restaurants
GROUP BY rag_mode
ORDER BY restaurant_count DESC;