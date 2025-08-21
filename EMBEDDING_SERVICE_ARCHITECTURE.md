# Embedding Service Architecture

## Current Situation
- Railway deployment doesn't have ML libraries (too large, no GPU)
- Text search fallback works but isn't as intelligent
- You have decentralized GPU resources available

## Recommended Architecture

### Option 1: Separate Embedding Microservice (BEST)
```
[Railway App] <--API--> [GPU Embedding Service]
     |                           |
     v                           v
[PostgreSQL]              [Your GPU Servers]
```

1. Create a separate embedding service on your GPU infrastructure
2. Railway app calls this service via API for:
   - Generating embeddings for new products
   - Similarity search queries
3. Store embeddings in PostgreSQL (as we do now)

### Option 2: Batch Processing
1. Generate embeddings offline on GPU servers
2. Upload to database periodically
3. Use pre-computed embeddings for search

### Option 3: Hybrid Approach
1. Use OpenAI embeddings API (like in generate_embeddings_direct.py)
2. No GPU needed, just API calls
3. More expensive but works immediately

## Quick Implementation for Embedding API

```python
# embedding_api_service.py
from fastapi import FastAPI
from sentence_transformers import SentenceTransformer
import numpy as np

app = FastAPI()
model = SentenceTransformer('all-MiniLM-L6-v2')

@app.post("/embed")
def create_embedding(text: str):
    embedding = model.encode(text)
    return {"embedding": embedding.tolist()}

@app.post("/similarity")
def calculate_similarity(query: str, embeddings: List[List[float]]):
    query_emb = model.encode(query)
    similarities = []
    for emb in embeddings:
        similarity = np.dot(query_emb, emb) / (np.linalg.norm(query_emb) * np.linalg.norm(emb))
        similarities.append(float(similarity))
    return {"similarities": similarities}
```

Run this on your GPU server, then update the Railway app to call it.

## Storage Requirements
- Model size: ~80MB for all-MiniLM-L6-v2
- Libraries: ~400MB (transformers, torch, numpy)
- Total: ~500MB minimum

## For Immediate Use
The text search fallback I added will work fine for now. It searches by:
- Exact name matches
- Description content
- Tags and categories
- Smart term extraction (visa, work, retirement, etc.)

This ensures your legal business works TODAY while you set up the GPU service.