# Deployment Options for RAG

## Option 1: Deploy WITHOUT ML Libraries (Recommended for Railway)

This is the fastest and most stable option:

1. **Deploy with current Dockerfile** (no ML dependencies)
2. **RAG will be disabled** but chat still works perfectly
3. **Can enable RAG later** by installing ML libraries

Benefits:
- Fast deployment (~2 minutes)
- Lower memory usage
- No torch compatibility issues

## Option 2: Deploy WITH ML Libraries

Use the ML-enabled Dockerfile:

```bash
# In Railway settings, set custom Dockerfile:
railway.app/settings -> Build -> Dockerfile Path: Dockerfile.ml
```

Benefits:
- RAG enabled immediately
- Semantic search available

Drawbacks:
- Slow first deployment (~15 minutes)
- Higher memory usage (~1GB)
- May hit Railway limits

## Option 3: Use External Embedding Service

Instead of local embeddings, use:
- OpenAI Embeddings API
- Cohere Embed API
- HuggingFace Inference API

This requires modifying `embedding_service.py` to use API calls instead of local model.

## Option 4: Two-Stage Deployment

1. **First deploy without ML** (using current setup)
2. **SSH into Railway** and manually install:
   ```bash
   pip install -r requirements-ml.txt
   ```
3. **Restart the service**

## Recommended Approach

For Railway with limited resources:

1. **Deploy without ML first** (current setup)
2. **Test that everything works**
3. **If you need RAG**, either:
   - Upgrade Railway plan for more resources
   - Use external embedding API
   - Consider alternative hosting (Render, DigitalOcean)

## Environment Variables

```env
# Disable RAG if ML libraries not installed
USE_RAG=false

# Or use external embeddings
USE_EXTERNAL_EMBEDDINGS=true
EMBEDDING_API_KEY=your-key-here
```