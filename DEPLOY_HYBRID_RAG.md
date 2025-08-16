# 🚀 Deploy Smart Hybrid RAG

## Overview
The Smart Hybrid RAG automatically routes queries based on complexity:
- **Simple queries** → Optimized mode (fast, low cost)
- **Complex queries** → Enhanced V2 mode (better quality)

## Cost Benefits
- ~60% savings compared to all-enhanced mode
- Maintains quality for complex queries
- Faster responses for simple queries

## Deployment Steps

### 1. Update Environment Variable
Set the RAG mode to use smart hybrid routing:

```bash
RAG_MODE=hybrid_smart
```

### 2. Deploy to Railway
Push the changes and Railway will automatically deploy:

```bash
git add .
git commit -m "Enable smart hybrid RAG mode

- Automatic query complexity detection
- Routes simple queries to optimized mode
- Routes complex queries to enhanced_v2 mode
- ~60% cost savings vs all-enhanced

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>"
git push
```

### 3. Verify Deployment

#### Check Provider Info
```bash
curl https://restaurantchat-production.up.railway.app/provider
```

Should show:
```json
{
  "provider": "mia_rag_hybrid_smart",
  "rag_mode": "hybrid_smart"
}
```

#### Test Different Query Types

**Simple query (will use optimized):**
```bash
curl -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bella_vista_restaurant",
    "client_id": "test-123",
    "sender_type": "client",
    "message": "Hi! What pasta do you have?"
  }'
```

**Complex query (will use enhanced_v2):**
```bash
curl -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bella_vista_restaurant",
    "client_id": "test-123",
    "sender_type": "client",
    "message": "I am vegetarian but also allergic to nuts, what can I eat?"
  }'
```

## How It Works

### Query Complexity Detection
The system analyzes queries for:

1. **Simple Patterns** (→ optimized):
   - Greetings: "Hi", "Hello"
   - Basic info: "menu", "hours", "phone"
   - Simple questions: "price", "delivery"

2. **Complex Patterns** (→ enhanced_v2):
   - Multi-dietary: "vegetarian but also allergic"
   - Educational: "explain", "what's the difference"
   - Follow-ups: "actually, instead of..."
   - Multi-part: Multiple questions in one

### Routing Logic
```python
# Complexity score based on:
- Pattern matching
- Message length (>100 chars)
- Multiple sentences
- Specific complexity indicators

if complexity_score >= 2:
    use enhanced_v2
elif complexity_score == 1 and certain_types:
    use enhanced_v2
else:
    use optimized
```

## Monitoring

### Check Logs
Look for routing decisions in logs:
```
Smart routing: optimized (reason: simple_query)
Smart routing: enhanced_v2 (reason: ['multi_dietary'])
```

### Cost Analysis
With typical usage (80% simple, 20% complex):
- 10,000 queries/month: $26.40 (vs $60 all-enhanced)
- 50,000 queries/month: $132 (vs $300 all-enhanced)

## Rollback
To rollback to a single mode:
```bash
# Use only optimized (lowest cost)
RAG_MODE=optimized

# Use only enhanced_v2 (best quality)
RAG_MODE=enhanced_v2
```

## Future Improvements
- Add conversation memory detection
- Fine-tune complexity thresholds based on usage
- Add per-restaurant customization
- Track actual cost savings

## Support
If you notice issues with routing:
1. Check logs for routing decisions
2. Adjust complexity patterns in `rag_chat_hybrid_smart.py`
3. Monitor quality metrics