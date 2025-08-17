# Setting Up Redis on Railway

## Option 1: Add Redis Service to Railway (Recommended)

1. **In Railway Dashboard**:
   - Click "New Service" → "Database" → "Redis"
   - Railway will provision a Redis instance
   - Get the connection URL from the Redis service

2. **Update .env**:
   ```env
   REDIS_URL=redis://default:password@redis.railway.internal:6379
   ```

3. **Update redis_helper.py** to use Railway Redis:
   ```python
   import os
   redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379')
   ```

## Option 2: Ensure Redis Package Installs

1. **Check Railway build logs** for any pip install failures
2. **Verify Python version** matches local development
3. **Alternative requirements.txt**:
   ```
   redis>=5.0.1
   hiredis>=2.0.0  # C extension for better performance
   ```

## Option 3: Use External Redis Provider

1. **Redis Cloud** (free tier available):
   - Sign up at redislabs.com
   - Create free database
   - Get connection string
   - Add to Railway environment variables

2. **Upstash** (serverless Redis):
   - Better for low-traffic apps
   - Pay per request model
   - Works well with Railway

## Testing Redis Connection

Add this endpoint to test Redis:

```python
@router.get("/test-redis")
async def test_redis():
    from services.redis_helper import redis_client
    
    try:
        # Test set/get
        redis_client.setex("test_key", 60, "test_value")
        value = redis_client.get("test_key")
        
        return {
            "redis_available": redis_client._redis_available,
            "test_successful": value == "test_value",
            "using_mock": not redis_client._redis_available
        }
    except Exception as e:
        return {
            "redis_available": False,
            "error": str(e),
            "using_mock": True
        }
```

## Why Lazy Import Works

The lazy import pattern delays the Redis import until it's actually needed:

1. **Module loads successfully** - No import errors
2. **First Redis access** - Tries to import and connect
3. **Automatic fallback** - Uses in-memory if Redis fails
4. **No service crashes** - Graceful degradation

This way, all your enhanced services can work with or without Redis!