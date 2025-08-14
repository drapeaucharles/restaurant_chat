# RAG Deployment Checklist

## 1. ✅ Environment Variables Added
You've added these to Railway:
- `HUGGINGFACE_API_KEY` ✓
- `USE_LIGHTWEIGHT_EMBEDDINGS=true` ✓
- `USE_RAG=true` ✓
- `REDIS_URL` ✓

## 2. ⏳ Wait for Deployment
- Check Railway dashboard for deployment status
- First deployment may take 5-10 minutes
- Look for green checkmark in Railway

## 3. 🔍 Verify Deployment
Once deployed, check:
```bash
curl https://restaurantchat-production.up.railway.app/
```

Should show version: `v7-rag-lightweight-READY`

## 4. 🗄️ Setup Database (if pgvector available)

### Option A: Using Railway CLI
```bash
# Install Railway CLI if needed
npm install -g @railway/cli

# Login and link project
railway login
railway link

# Run migration
railway run python run_migrations.py

# If migration fails due to permissions:
railway run python check_pgvector.py
```

### Option B: Manual PostgreSQL
```bash
# Connect to your Railway PostgreSQL
railway connect postgres

# Run in PostgreSQL:
CREATE EXTENSION IF NOT EXISTS vector;
```

## 5. 📚 Index Menu Items

### If pgvector is available:
```bash
railway run python index_menu_local.py bella_vista_restaurant
```

### If pgvector is NOT available:
- The system will use hash-based embeddings (fallback)
- Still provides basic semantic search
- Not as accurate but works!

## 6. ✅ Test RAG

Test semantic search:
```bash
# Simple health query
curl -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bella_vista_restaurant",
    "client_id": "550e8400-e29b-41d4-a716-446655440000",
    "sender_type": "client",
    "message": "What healthy options do you have?"
  }'
```

## 7. 🎯 Expected Results

With RAG enabled, queries like these will work better:
- "Something light for lunch" → Finds salads, soups
- "Vegetarian pasta" → Filters to specific options
- "Gluten-free dishes" → Understands dietary needs
- "Seafood options" → Finds all seafood items

## Troubleshooting

### If deployment fails:
1. Check Railway logs for errors
2. Verify all environment variables are set
3. Try redeploying

### If pgvector not available:
- Contact Railway support to enable pgvector
- Or just use the fallback (still works!)

### If chat returns empty:
- Check if client creation is working
- Verify restaurant exists in database

## Status Indicators

✅ = Complete
⏳ = In Progress
❌ = Failed/Blocked
🔄 = Retry needed

Your current status: Deployment in progress ⏳