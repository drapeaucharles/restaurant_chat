# GPU Embedding Service Setup Guide

## Overview
This service runs on your decentralized GPU infrastructure to provide secure embeddings without exposing sensitive business data.

## Setup Steps

### 1. Choose GPU Servers
Select 2-3 GPU servers for redundancy. Each should have:
- NVIDIA GPU with CUDA support
- Docker with nvidia-docker runtime
- At least 4GB GPU memory
- Public IP or domain

### 2. Deploy on Each GPU Server

```bash
# Clone the gpu_embedding_service directory
cd gpu_embedding_service

# Build and run with Docker Compose
docker-compose up -d

# Or without Docker Compose
docker build -t embedding-service .
docker run -d -p 8080:8080 --gpus all embedding-service
```

### 3. Test the Service

```bash
# Health check
curl http://your-gpu-server:8080/health

# Test embedding
curl -X POST http://your-gpu-server:8080/embed \
  -H "Content-Type: application/json" \
  -d '{"text": "test embedding generation"}'
```

### 4. Configure Railway App

Add environment variables to your Railway app:

```env
# Comma-separated list of GPU endpoints
GPU_EMBEDDING_ENDPOINTS=http://gpu1.example.com:8080,http://gpu2.example.com:8080

# Optional settings
GPU_EMBEDDING_TIMEOUT=5.0
GPU_EMBEDDING_RETRIES=2
```

### 5. Update Embedding Service

In `embedding_service_universal.py`, update to use GPU client:

```python
async def create_embedding_async(self, text: str) -> Optional[List[float]]:
    """Create embedding using GPU service"""
    from services.gpu_embedding_client import gpu_embedding_client
    return await gpu_embedding_client.get_embedding(text)
```

## Security Features

✅ **Data Protection**:
- Text is anonymized before sending
- No storage on GPU servers
- Stateless operation
- Request logging without content

✅ **Network Security**:
- Use HTTPS in production
- Firewall GPU servers to only allow Railway
- Rotate GPU endpoints regularly
- Monitor for unusual activity

## Monitoring

### Check GPU Service Health
```python
from services.gpu_embedding_client import gpu_embedding_client
import asyncio

async def check_gpus():
    health = await gpu_embedding_client.check_health()
    for endpoint, status in health.items():
        print(f"{endpoint}: {status}")

asyncio.run(check_gpus())
```

### Logs
GPU servers only log:
- Request counts
- Processing times
- Text hashes (not content)
- Errors

## Scaling

### Horizontal Scaling
- Add more GPU servers to the endpoint list
- Load is automatically distributed

### Vertical Scaling
- Use larger GPUs for faster processing
- Batch requests for efficiency

### Model Options
- `all-MiniLM-L6-v2`: Fast, good quality (default)
- `all-mpnet-base-v2`: Better quality, slower
- `paraphrase-multilingual-MiniLM-L12-v2`: Multilingual support

## Troubleshooting

### GPU Out of Memory
- Reduce batch size
- Use smaller model
- Restart service to clear cache

### Slow Response
- Check GPU utilization
- Add more GPU servers
- Reduce model size

### Connection Errors
- Check firewall rules
- Verify endpoints in Railway
- Test health endpoint

## Cost Optimization

1. **Use Spot Instances**: GPU servers can be spot/preemptible
2. **Auto-scaling**: Scale down during low usage
3. **Batch Processing**: Group requests for efficiency
4. **Cache Common Embeddings**: On Railway side (not GPU)