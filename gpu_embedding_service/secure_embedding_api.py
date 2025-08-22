"""
Secure Embedding API Service for Decentralized GPU
Runs on your GPU infrastructure - stateless and secure
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import hashlib
import time
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Secure Embedding Service", version="1.0.0")

# CORS for Railway access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://restaurantchat-production.up.railway.app"],
    allow_methods=["POST"],
    allow_headers=["Content-Type"],
)

# Load model at startup
MODEL = None
MODEL_NAME = "all-MiniLM-L6-v2"  # Small, fast, good quality

@app.on_event("startup")
async def load_model():
    global MODEL
    logger.info(f"Loading model {MODEL_NAME}...")
    MODEL = SentenceTransformer(MODEL_NAME)
    logger.info(f"Model loaded successfully. Dimension: {MODEL.get_sentence_embedding_dimension()}")

# Request/Response models
class EmbeddingRequest(BaseModel):
    text: str = Field(..., max_length=1000, description="Text to embed")
    request_id: Optional[str] = Field(None, description="Optional request ID for tracking")

class BatchEmbeddingRequest(BaseModel):
    texts: List[str] = Field(..., max_items=100, description="Batch of texts")
    request_id: Optional[str] = Field(None, description="Optional request ID")

class EmbeddingResponse(BaseModel):
    embedding: List[float]
    dimension: int
    model_used: str
    processing_time_ms: float

class BatchEmbeddingResponse(BaseModel):
    embeddings: List[List[float]]
    dimension: int
    model_used: str
    processing_time_ms: float
    count: int

class HealthResponse(BaseModel):
    status: str
    model_loaded: bool
    model_name: str
    embedding_dimension: int
    timestamp: str

# Security middleware - log requests but don't store data
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    # Log request (but not the body content)
    logger.info(f"Request from {request.client.host} to {request.url.path}")
    
    response = await call_next(request)
    
    # Log response time
    process_time = time.time() - start_time
    logger.info(f"Request processed in {process_time:.3f}s")
    
    return response

@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint"""
    return HealthResponse(
        status="healthy" if MODEL else "model_not_loaded",
        model_loaded=MODEL is not None,
        model_name=MODEL_NAME,
        embedding_dimension=MODEL.get_sentence_embedding_dimension() if MODEL else 0,
        timestamp=datetime.utcnow().isoformat()
    )

@app.post("/embed", response_model=EmbeddingResponse)
async def create_embedding(request: EmbeddingRequest):
    """Create embedding for a single text - stateless operation"""
    if not MODEL:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Generate embedding - no storage, no memory
        embedding = MODEL.encode(request.text)
        
        processing_time = (time.time() - start_time) * 1000
        
        # Log hash of text for debugging (not the actual text)
        text_hash = hashlib.sha256(request.text.encode()).hexdigest()[:8]
        logger.info(f"Generated embedding for text hash: {text_hash}")
        
        return EmbeddingResponse(
            embedding=embedding.tolist(),
            dimension=len(embedding),
            model_used=MODEL_NAME,
            processing_time_ms=processing_time
        )
    except Exception as e:
        logger.error(f"Embedding generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Embedding generation failed")

@app.post("/embed/batch", response_model=BatchEmbeddingResponse)
async def create_batch_embeddings(request: BatchEmbeddingRequest):
    """Create embeddings for multiple texts - more efficient"""
    if not MODEL:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    start_time = time.time()
    
    try:
        # Generate embeddings in batch
        embeddings = MODEL.encode(request.texts)
        
        processing_time = (time.time() - start_time) * 1000
        
        logger.info(f"Generated {len(request.texts)} embeddings in batch")
        
        return BatchEmbeddingResponse(
            embeddings=[emb.tolist() for emb in embeddings],
            dimension=embeddings.shape[1],
            model_used=MODEL_NAME,
            processing_time_ms=processing_time,
            count=len(embeddings)
        )
    except Exception as e:
        logger.error(f"Batch embedding generation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Batch embedding generation failed")

@app.post("/similarity")
async def calculate_similarity(query_embedding: List[float], candidate_embeddings: List[List[float]]):
    """Calculate cosine similarity between query and candidates"""
    try:
        query_vec = np.array(query_embedding)
        candidates = np.array(candidate_embeddings)
        
        # Normalize vectors
        query_norm = query_vec / np.linalg.norm(query_vec)
        candidates_norm = candidates / np.linalg.norm(candidates, axis=1, keepdims=True)
        
        # Calculate cosine similarities
        similarities = np.dot(candidates_norm, query_norm)
        
        return {
            "similarities": similarities.tolist(),
            "count": len(similarities)
        }
    except Exception as e:
        logger.error(f"Similarity calculation failed: {str(e)}")
        raise HTTPException(status_code=500, detail="Similarity calculation failed")

if __name__ == "__main__":
    import uvicorn
    # Run with GPU support if available
    uvicorn.run(app, host="0.0.0.0", port=8080)