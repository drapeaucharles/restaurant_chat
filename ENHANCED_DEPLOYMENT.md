# Enhanced MIA Chat Service - Deployment Guide

## Overview
This guide explains how to deploy the enhanced MIA chat service with immediate improvements:
- 🎭 Enhanced system prompts with role-playing
- 💾 Redis-based response caching
- 🌡️ Dynamic temperature adjustment
- 🌍 Multi-language support
- 🔍 Query type detection

## Files Created/Modified

### New Files:
1. `services/mia_chat_service_enhanced.py` - Enhanced service with all improvements
2. `config_enhanced.py` - Configuration for enhanced features
3. `routes/chat_enhanced.py` - Enhanced chat endpoints
4. `test_enhanced_chat.py` - Test suite for verification

## Local Testing

### 1. Install Redis (if not already installed)
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install redis-server

# Start Redis
sudo systemctl start redis
sudo systemctl enable redis  # Auto-start on boot

# Check if Redis is running
redis-cli ping  # Should return PONG
```

### 2. Install Python Redis client
```bash
cd /home/charles-drapeau/Documents/Project/Restaurant/BackEnd
pip install redis
```

### 3. Update main.py to use enhanced routes
```python
# In BackEnd/main.py, update the import:
# FROM:
from routes.chat import router as chat_router
# TO:
from routes.chat_enhanced import router as chat_router
```

### 4. Set environment variables
```bash
# Create or update .env file
cat >> .env << EOF
CHAT_PROVIDER=mia_enhanced
SKIP_LOCAL_MIA=true
REDIS_HOST=localhost
REDIS_PORT=6379
CACHE_ENABLED=true
EOF
```

### 5. Run the backend
```bash
python main.py
```

### 6. Test the enhancements
```bash
# In another terminal
cd /home/charles-drapeau/Documents/Project/Restaurant
python test_enhanced_chat.py
```

## Railway Deployment

### 1. Add Redis to Railway
```bash
# In Railway dashboard:
1. Go to your project
2. Click "New Service"
3. Select "Database" > "Redis"
4. Name it "redis-cache"
5. Note the connection details
```

### 2. Update Environment Variables
In Railway dashboard for your restaurant backend:
```
CHAT_PROVIDER=mia_enhanced
SKIP_LOCAL_MIA=true
REDIS_HOST=<redis-host-from-railway>
REDIS_PORT=<redis-port>
REDIS_PASSWORD=<redis-password>
CACHE_ENABLED=true
ENABLE_QUERY_ANALYSIS=true
ENABLE_DYNAMIC_TEMPERATURE=true
ENABLE_CONVERSATION_MEMORY=true
```

### 3. Update requirements.txt
```bash
# Add to BackEnd/requirements.txt
redis==5.0.1
```

### 4. Commit and Push
```bash
cd /home/charles-drapeau/Documents/Project/Restaurant
git add -A
git commit -m "Add enhanced MIA chat service with caching and improved prompts"
git push origin v3  # Make sure you're on v3 branch!
```

## Without Redis (Fallback)

If you can't use Redis, the service will still work with enhancements minus caching:

```bash
# Set environment variable
CACHE_ENABLED=false
```

The service will automatically disable caching and continue with other improvements.

## Verification

### Check Provider Info
```bash
curl http://localhost:8000/chat/provider
```

Expected response:
```json
{
  "mode": "enhanced_mia",
  "url": "https://mia-backend-production.up.railway.app",
  "features": [
    "Enhanced prompts with role-playing",
    "Redis-based caching",
    "Dynamic temperature adjustment",
    "Multi-language support",
    "Query type detection",
    "Conversation memory"
  ]
}
```

### Check Cache Stats
```bash
curl http://localhost:8000/chat/cache/stats
```

### Test Different Query Types

1. **Greeting** (High temperature, friendly):
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{
       "restaurant_id": "bella_vista_restaurant",
       "client_id": "test-123",
       "sender_type": "client",
       "message": "Hello!"
     }'
   ```

2. **Menu Query** (Low temperature, factual):
   ```bash
   curl -X POST http://localhost:8000/chat \
     -H "Content-Type: application/json" \
     -d '{
       "restaurant_id": "bella_vista_restaurant",
       "client_id": "test-123",
       "sender_type": "client",
       "message": "What pasta do you have?"
     }'
   ```

## Performance Improvements

### Expected Results:
- **First query**: 5-7 seconds (normal MIA response time)
- **Repeated query**: <100ms (cached)
- **Greetings**: More natural, no menu listing
- **Menu queries**: Complete listings with prices
- **Multi-language**: Automatic detection and response

### Cache Performance:
- Common queries cached for 1 hour
- Greetings cached for 24 hours
- Restaurant-specific caching
- Language-aware cache keys

## Monitoring

### View Logs
```bash
# Local
tail -f restaurant.log | grep -E "(ENHANCED|Cache|Query analysis)"

# Railway
railway logs --service=restaurant-backend | grep -E "(ENHANCED|Cache)"
```

### Clear Cache if Needed
```bash
# Clear all cache
curl -X POST http://localhost:8000/chat/cache/clear

# Clear specific restaurant
curl -X POST http://localhost:8000/chat/cache/clear?restaurant_id=bella_vista_restaurant
```

## Rollback Plan

If issues occur, rollback to standard service:
1. Change `CHAT_PROVIDER=mia` (from `mia_enhanced`)
2. Update import in main.py back to original
3. Restart service

## Next Steps

After verifying immediate improvements work:
1. **Week 2-3**: Implement RAG for better context
2. **Month 2**: Add async processing and queues
3. **Month 3+**: Auto-scaling and advanced monitoring

The enhanced service is backward compatible and can be deployed without breaking existing functionality!