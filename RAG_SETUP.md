# RAG (Retrieval Augmented Generation) Setup Guide

## Overview
RAG enhances the chat system with semantic search capabilities, allowing better understanding of:
- Vague queries ("something healthy")
- Dietary restrictions ("gluten-free options")
- Ingredient-based searches ("dishes with seafood")
- Similarity-based recommendations

## Architecture
```
User Query → Embedding → Vector Search → Relevant Items → Enhanced Context → Better AI Response
```

## Setup Steps

### 1. Check PostgreSQL pgvector Support

First, check if pgvector is available:
```bash
python check_pgvector.py
```

If pgvector is not available on Railway, you have options:
- Contact Railway support to enable pgvector
- Use alternative deployment (Supabase has pgvector by default)
- Disable RAG with `USE_RAG=false`

### 2. Run Database Migration

If pgvector is available:
```bash
python run_migrations.py
```

Or manually with SQL:
```bash
psql $DATABASE_URL < migrations/pgvector_manual.sql
```

### 3. Index Menu Items

#### Option A: Via API (Remote)
```bash
# Get auth token first
curl -X POST https://your-api.railway.app/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "password"}'

# Index menu
curl -X POST https://your-api.railway.app/embeddings/index/bella_vista_restaurant \
  -H "Authorization: Bearer YOUR_TOKEN"
```

#### Option B: Local Script (On Server)
```bash
python index_menu_local.py bella_vista_restaurant
```

#### Option C: Complete Setup Script
```bash
python setup_rag.py
```

### 4. Verify Setup

Check indexing status:
```bash
curl https://your-api.railway.app/embeddings/status/bella_vista_restaurant
```

Test semantic search:
```bash
curl -X POST https://your-api.railway.app/embeddings/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "healthy vegetarian options",
    "restaurant_id": "bella_vista_restaurant",
    "limit": 5
  }'
```

## Environment Variables

```env
# Enable/disable RAG (default: true)
USE_RAG=true

# Model cache directory (optional)
MODEL_CACHE_DIR=/app/model_cache
```

## How It Works

1. **Indexing Phase**:
   - Each menu item is converted to text including name, description, ingredients
   - Text is converted to 384-dimensional vector using all-MiniLM-L6-v2
   - Vectors stored in PostgreSQL with pgvector

2. **Search Phase**:
   - User query is converted to vector
   - Cosine similarity search finds most relevant menu items
   - Top 5 items provided as context to AI

3. **Response Generation**:
   - AI receives relevant items as context
   - Maria personality responds with accurate information
   - No hallucination of non-existent menu items

## Troubleshooting

### pgvector Not Available
```
Error: pgvector extension is NOT available
```
**Solution**: Contact Railway support or use alternative PostgreSQL provider

### Permission Denied
```
Error: permission denied to create extension "vector"
```
**Solution**: Need superuser access. Ask DB admin to run:
```sql
CREATE EXTENSION vector;
```

### Model Download Slow
First deployment downloads ~90MB model. Subsequent deployments use cache.

### Out of Memory
If Railway instance has limited memory:
1. Use smaller model in `embedding_service.py`
2. Or disable RAG: `USE_RAG=false`

## Testing Queries

After setup, try these enhanced queries:
- "What are your healthiest options?"
- "I'm vegetarian, what do you recommend?"
- "Something light for lunch"
- "Dishes without dairy"
- "Your most popular seafood items"

## Performance

- Initial indexing: ~1-2 seconds per 100 items
- Search latency: ~50-100ms
- Memory usage: ~500MB for model
- Storage: ~1KB per menu item

## Fallback Behavior

If RAG fails or is disabled:
- System automatically uses keyword search
- No errors shown to users
- Slightly less accurate but still functional

## Monitoring

Check RAG usage:
```bash
curl https://your-api.railway.app/embeddings/stats
```

View logs:
```bash
railway logs | grep -E "(RAG|embedding|vector)"
```