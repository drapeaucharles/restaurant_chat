# Redis Setup for Restaurant Backend on Railway

## Quick Setup

1. **Add Redis to your Railway project:**
   - Go to your Railway project dashboard
   - Click "New Service"
   - Select "Database" → "Add Redis"
   - Railway will automatically provision a Redis instance

2. **Connect Redis to Restaurant Backend:**
   - In your Restaurant Backend service settings
   - Go to "Variables" tab
   - Add reference variable:
     ```
     REDIS_HOST=${{Redis.REDIS_HOST}}
     REDIS_PORT=${{Redis.REDIS_PORT}}
     ```
   - Or use the full URL:
     ```
     REDIS_URL=${{Redis.REDIS_URL}}
     ```

3. **Verify Redis is connected:**
   - After deployment, check: `https://restaurantchat-production.up.railway.app/cache/stats`
   - Should show: `"redis_available": true`

## What Redis Enables

- **Response Caching**: Faster responses for repeated questions
- **Multi-language caching**: Separate cache for EN/ES/FR
- **24-hour cache for greetings**: Consistent welcome messages
- **1-hour cache for menu queries**: Balance between freshness and speed

## Fallback Mode

If Redis is not configured or unavailable:
- System automatically uses in-memory caching
- No errors or service interruption
- Just slightly slower for repeated queries

## Cost

- Redis on Railway: ~$5/month for basic instance
- Sufficient for restaurant chat caching needs

## Environment Variables (Optional)

```env
# Basic config (Railway auto-provides these)
REDIS_HOST=your-redis-host
REDIS_PORT=6379

# Or use URL format
REDIS_URL=redis://your-redis-url

# Optional settings
REDIS_DB=0
CACHE_ENABLED=true
CACHE_TTL_GENERAL=3600
CACHE_TTL_GREETING=86400
```