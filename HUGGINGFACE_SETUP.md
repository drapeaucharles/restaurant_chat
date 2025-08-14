# HuggingFace API Setup for RAG

## Get Your Free API Key (2 minutes)

1. **Create HuggingFace Account**
   - Go to: https://huggingface.co/join
   - Sign up (free)

2. **Get API Token**
   - Go to: https://huggingface.co/settings/tokens
   - Click "New token"
   - Name: "Restaurant RAG"
   - Role: "read"
   - Click "Generate"

3. **Add to Railway**
   ```
   HUGGINGFACE_API_KEY=hf_xxxxxxxxxxxxxxxxxxxxxxxxxx
   USE_LIGHTWEIGHT_EMBEDDINGS=true
   USE_RAG=true
   ```

## Benefits

- **No ML libraries needed** on Railway
- **Fast deployment** (2 minutes)
- **Low memory usage** (~200MB vs 1GB)
- **Good quality embeddings** (same model)
- **Free tier**: 30,000 requests/month

## How It Works

1. Menu items sent to HuggingFace API
2. API returns embeddings
3. Stored in PostgreSQL with pgvector
4. Used for semantic search

## Fallback

If API fails or no key provided:
- Uses hash-based embeddings
- Not as good but still works
- Better than no RAG at all

## Test Your Setup

After adding the API key:

```bash
# Check if embeddings work
curl -X POST https://your-api.railway.app/embeddings/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "vegetarian pasta",
    "restaurant_id": "bella_vista_restaurant"
  }'
```

## Cost

- **Free tier**: 30,000 API calls/month
- **Menu indexing**: ~50-100 calls per restaurant
- **Search**: 1 call per query
- **Plenty for most restaurants**

## Alternative: OpenAI Embeddings

If you already have OpenAI API key:
1. Modify `embedding_service_lite.py`
2. Use `text-embedding-3-small`
3. $0.02 per 1M tokens (~2000 searches)