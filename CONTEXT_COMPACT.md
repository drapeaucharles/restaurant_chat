# MIA Project Context - Compact Summary

## Current State
- **Architecture**: Full menu approach (all businesses using `full_menu` mode)
- **Response Time**: 9-12 seconds (optimized from 15-22s)
- **Customer Memory**: ✅ Working (names and preferences saved)
- **All businesses**: Using full_menu mode

## Journey & Learnings

### 1. Started With
- Memory not working (AI couldn't remember names)
- Slow responses (15-22 seconds)
- Restaurant falling back to wrong mode

### 2. What We Built
- **db_query service**: AI fetches only needed data (77% smaller prompts)
- **Pattern matching**: "I like tomato", "What appetizers?", etc.
- **Fast polling**: Reduced MIA response time by 40%
- **Pre-warming**: Keeps MIA model hot

### 3. What We Learned
- Pattern matching doesn't scale across business types
- Embeddings miss complex queries
- Guessing user intent is fragile
- MIA's bottleneck is token generation, not prompt size

### 4. The Better Solution
**Full Menu + AI Queries**
- Send compact catalog (name, price, category)
- Let AI decide when it needs details
- AI calls: `GET_DETAILS("item_name")`
- Universal for any business type

## Next Architecture

### Restaurant Backend
```
Sends to MIA:
- Full catalog (compact, no descriptions)
- API endpoint for detail queries
- Customer memory context
```

### MIA Miner (Needs Update)
```
Current: Qwen2.5-7B (no function calling)
Recommended: Command-R-7B
- Native function calling
- Excellent multilingual (EN/FR/RU/ID)
- Customer support optimized
```

### Flow
1. User: "What's in the lobster ravioli?"
2. Backend: Sends compact menu + query API info
3. MIA: Recognizes need for details
4. MIA: Calls `GET_DETAILS("Lobster Ravioli")`
5. MIA: Generates complete response

## Key Insights
- Don't guess what users want - let AI decide
- Full context prevents missing items
- Details on demand keeps prompts small
- One system works for all business types
- Quality > Speed (9-12s is acceptable)

## Technical Details
- **Models Evaluated**: Llama-3.2, Command-R, DeepSeek, Qwen
- **Winner**: Command-R-7B (function calling + languages + customer support)
- **MIA Stack**: vLLM + AWQ quantization + Qwen2.5-7B
- **Actual Speed**: ~20-30 tokens/sec (not 60+ as claimed)

## Files to Keep
- `/services/mia_fast_polling.py` - Still useful
- `/services/mia_prewarm.py` - Still useful
- `/services/customer_memory_service.py` - Fixed and working
- All test scripts for reference

## Status: Ready for Next Phase
- ✅ Memory working
- ✅ Response times optimized
- ✅ All businesses on full_menu
- 🔄 Next: Implement compact full_menu + function calling