# Deploy Optimized Memory RAG Mode

## Changes Made

1. **Created new service**: `services/rag_chat_optimized_with_memory.py`
   - Based on the working `optimized` service (the only one that works on Railway)
   - Added simple memory functionality without Redis or complex dependencies
   - Captures customer names and uses them in responses
   - Maintains conversation history (last 5 exchanges)

2. **Updated router**: `routes/chat_dynamic.py`
   - Added import for `optimized_with_memory` service
   - Service will be available as a selectable RAG mode

3. **Database update needed**: Run this SQL on Railway PostgreSQL:
   ```sql
   UPDATE restaurants 
   SET rag_mode = 'optimized_with_memory'
   WHERE rag_mode IS NOT NULL;
   ```

## Key Features of optimized_with_memory

- **Name Recognition**: Detects "my name is X" patterns and remembers customer names
- **Personalized Responses**: Uses customer name in greetings when known
- **Simple Memory**: Stores last 5 conversation exchanges per customer
- **No Redis**: Uses in-memory Python dictionary (works on Railway)
- **Based on Working Code**: Modified from the optimized service that already works

## Deployment Steps

1. Deploy the code changes to Railway
2. Run the SQL update to switch all restaurants to the new mode
3. Test with:
   - "Hello my name is Charles"
   - "Can you call me by my name"
   - "What kind of pasta do you have"

## Why This Should Work

- Uses the exact same base as the `optimized` service which works on Railway
- No new dependencies or imports that could fail
- Simple Python dictionary for memory (no Redis)
- Minimal changes to proven working code