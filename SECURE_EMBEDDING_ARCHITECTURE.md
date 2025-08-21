# Secure Embedding Architecture for Decentralized GPUs

## Security Principle
**Never send actual business data to untrusted GPUs!**

## Secure Architecture

### 1. Stateless Embedding Service (RECOMMENDED)
```
[Railway App] --> [Decentralized GPU]
    |                     |
    v                     v
"Generate embedding   Just returns numbers
 for this text"      No storage, no memory
```

**How it works:**
- GPU service ONLY converts text to vectors
- Never stores anything
- Stateless - each request is independent
- No database access

### 2. Two-Stage Processing
```python
# On Railway (trusted):
def prepare_for_embedding(product):
    # Anonymize sensitive data
    safe_text = f"Service type: {product.category} | Features: {', '.join(product.features)}"
    # Don't send: prices, customer data, business names
    return safe_text

# On GPU (untrusted):
def create_embedding(text):
    # Only sees generic text
    return model.encode(text)
```

### 3. Secure GPU Service Implementation

```python
# secure_embedding_service.py (runs on decentralized GPU)
from fastapi import FastAPI, HTTPException
from sentence_transformers import SentenceTransformer
from pydantic import BaseModel
import logging

app = FastAPI()
model = SentenceTransformer('all-MiniLM-L6-v2')

# Security: No database connection
# Security: No file system access
# Security: No state storage

class EmbeddingRequest(BaseModel):
    text: str
    # Limit text size to prevent abuse
    class Config:
        max_length = 1000

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int

@app.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """Convert text to embedding vector - stateless operation"""
    try:
        # Security: Only process, never store
        embedding = model.encode(request.text)
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            dimension=len(embedding)
        )
    except Exception as e:
        # Don't leak internal errors
        raise HTTPException(status_code=500, detail="Embedding generation failed")

# No other endpoints - single purpose service
```

### 4. Railway Integration (Secure Client)

```python
# embedding_client_secure.py
import httpx
from typing import List, Optional
import hashlib

class SecureEmbeddingClient:
    def __init__(self, gpu_endpoints: List[str]):
        self.endpoints = gpu_endpoints
        
    def anonymize_product_text(self, product: dict) -> str:
        """Remove sensitive data before sending to GPU"""
        # Only send generic features
        parts = []
        
        if product.get('category'):
            parts.append(f"Category: {product['category']}")
            
        if product.get('product_type'):
            parts.append(f"Type: {product['product_type']}")
            
        # Hash any identifiers instead of sending them
        if product.get('name'):
            name_hash = hashlib.sha256(product['name'].encode()).hexdigest()[:8]
            parts.append(f"Item: {name_hash}")
            
        # Generic features only
        if product.get('features'):
            parts.append(f"Features: {len(product['features'])} included")
            
        return " | ".join(parts)
    
    async def get_embedding(self, text: str) -> Optional[List[float]]:
        """Get embedding from untrusted GPU"""
        # Try multiple endpoints for redundancy
        for endpoint in self.endpoints:
            try:
                async with httpx.AsyncClient(timeout=5.0) as client:
                    response = await client.post(
                        f"{endpoint}/embed",
                        json={"text": text},
                        # Don't send any auth tokens or identifiers
                    )
                    if response.status_code == 200:
                        return response.json()["embedding"]
            except:
                continue
        return None
```

### 5. Security Checklist

✅ **What GPU servers DON'T see:**
- Business names
- Real product names
- Prices
- Customer data
- Database credentials
- API keys
- Internal IDs

✅ **What GPU servers DO see:**
- Generic text descriptions
- Categories and types
- Feature counts
- Anonymized data

✅ **Additional Security:**
- Use multiple GPU endpoints (redundancy)
- Timeout requests (prevent hanging)
- Rate limiting
- No persistent connections
- Rotate GPU endpoints regularly

### 6. For Maximum Security: Local Embeddings

If even anonymized data is too sensitive, use lightweight models locally:
```python
# Use TF-IDF instead of neural embeddings
from sklearn.feature_extraction.text import TfidfVectorizer

# Runs on Railway, no GPU needed
vectorizer = TfidfVectorizer(max_features=384)
embeddings = vectorizer.fit_transform(texts)
```

This is less accurate but 100% secure and runs without GPU.