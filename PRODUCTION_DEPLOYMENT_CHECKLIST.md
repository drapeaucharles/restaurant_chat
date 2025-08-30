# Production Deployment Checklist - DB Query Update

## 1. Restaurant Backend (Railway)

### Auto-Deploy (if configured):
- Railway should auto-deploy from the v3 branch
- Check Railway dashboard for deployment status

### Manual Deploy (if needed):
```bash
# On Railway dashboard
1. Go to your restaurant-backend service
2. Click "Redeploy" 
3. Or use Railway CLI:
railway up
```

### After Deploy:
```bash
# SSH into Railway or use Railway run
railway run python update_all_to_db_query.py
```

## 2. MIA Backend (No Changes Needed)

The MIA miner **doesn't need updates** because:
- DB query changes are only in the restaurant backend
- MIA still receives the same prompt format
- We only changed what data we send to MIA

## 3. Verify Deployment

### Check Services Available:
```bash
curl https://restaurantchat-production.up.railway.app/provider
```

### Test DB Query:
```bash
curl -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bella_vista_restaurant",
    "client_id": "test-deploy-001",
    "sender_type": "client",
    "message": "I like pasta"
  }'
```

## 4. Production Monitoring

Watch for:
- Response times should be 9-12s
- Check logs for "Using fast polling for MIA"
- Verify businesses are using db_query mode

## 5. Required Environment Variables

Ensure these are set in Railway:
```
DATABASE_URL=<your-postgres-url>
REDIS_URL=<your-redis-url>
MIA_BACKEND_URL=https://mia-backend-production.up.railway.app
DEFAULT_RAG_MODE=db_query
```

## Summary

Only the **Restaurant Backend** needs deployment. MIA stays the same!