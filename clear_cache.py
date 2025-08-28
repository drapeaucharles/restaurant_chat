import sys
sys.path.append('.')

import redis
import os
from urllib.parse import urlparse

# Get Redis connection info
REDIS_URL = os.getenv("REDIS_URL")

if REDIS_URL:
    parsed = urlparse(REDIS_URL)
    redis_client = redis.Redis(
        host=parsed.hostname,
        port=parsed.port or 6379,
        password=parsed.password,
        decode_responses=True
    )
else:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        password=os.getenv("REDIS_PASSWORD"),
        decode_responses=True
    )

try:
    # Connect to Redis
    redis_client.ping()
    print("Connected to Redis successfully!")
    
    # Find all cache keys related to eggs
    all_keys = redis_client.keys("*")
    egg_keys = []
    
    for key in all_keys:
        if any(word in key.lower() for word in ['egg', 'love', 'like']):
            egg_keys.append(key)
            print(f"Found key: {key}")
    
    if egg_keys:
        print(f"\nDeleting {len(egg_keys)} cache entries...")
        for key in egg_keys:
            redis_client.delete(key)
        print("Cache cleared!")
    else:
        print("\nNo egg-related cache entries found")
        
    # Show all cache keys for bella_vista
    print("\n\nAll bella_vista cache keys:")
    bella_keys = [k for k in all_keys if 'bella_vista' in k.lower()]
    for key in bella_keys[:10]:
        print(f"  {key}")
    
except redis.ConnectionError:
    print("Could not connect to Redis. Cache might be in-memory only.")
except Exception as e:
    print(f"Error: {e}")