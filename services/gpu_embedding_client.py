"""
GPU Embedding Client for Railway
Connects to secure embedding service on decentralized GPU
"""
import os
import httpx
import logging
import hashlib
from typing import List, Optional, Dict
import asyncio
from datetime import datetime
import json

logger = logging.getLogger(__name__)

class GPUEmbeddingClient:
    """Client for secure GPU embedding service"""
    
    def __init__(self, gpu_endpoints: Optional[List[str]] = None):
        """Initialize with GPU endpoints"""
        # Get endpoints from environment or use defaults
        if gpu_endpoints:
            self.endpoints = gpu_endpoints
        else:
            endpoints_str = os.getenv("GPU_EMBEDDING_ENDPOINTS", "")
            if endpoints_str:
                self.endpoints = [e.strip() for e in endpoints_str.split(",")]
            else:
                # Default endpoints (update with your actual GPU service URLs)
                self.endpoints = [
                    "http://gpu1.example.com:8080",
                    "http://gpu2.example.com:8080"
                ]
        
        self.timeout = float(os.getenv("GPU_EMBEDDING_TIMEOUT", "5.0"))
        self.max_retries = int(os.getenv("GPU_EMBEDDING_RETRIES", "2"))
        
    def anonymize_text(self, text: str, business_type: str = "generic") -> str:
        """
        Anonymize text before sending to GPU
        Removes business names, prices, and sensitive data
        """
        # Hash any potential identifiers
        text_lower = text.lower()
        
        # Remove prices
        import re
        text = re.sub(r'\$[\d,]+\.?\d*', 'PRICE', text)
        
        # Remove email addresses
        text = re.sub(r'\S+@\S+', 'EMAIL', text)
        
        # Remove phone numbers
        text = re.sub(r'\+?\d{10,}', 'PHONE', text)
        
        # Business-specific anonymization
        if business_type == "legal_visa":
            # Keep service types but remove specific names
            text = re.sub(r'([A-Z][a-z]+ ){2,}(Consulting|Services|Law)', 'COMPANY', text)
        elif business_type == "restaurant":
            # Keep food types but remove restaurant names
            text = re.sub(r'(Restaurant|Bistro|Cafe|Bar)\s+\w+', 'RESTAURANT', text)
        
        return text
    
    async def get_embedding(self, text: str, anonymize: bool = True) -> Optional[List[float]]:
        """Get embedding from GPU service with fallback"""
        if anonymize:
            text = self.anonymize_text(text)
        
        # Try each endpoint
        for endpoint in self.endpoints:
            for attempt in range(self.max_retries):
                try:
                    async with httpx.AsyncClient(timeout=self.timeout) as client:
                        response = await client.post(
                            f"{endpoint}/embed",
                            json={"text": text},
                            headers={"Content-Type": "application/json"}
                        )
                        
                        if response.status_code == 200:
                            data = response.json()
                            logger.info(f"Got embedding from {endpoint}")
                            return data["embedding"]
                        else:
                            logger.warning(f"GPU service returned {response.status_code}")
                            
                except Exception as e:
                    logger.warning(f"GPU endpoint {endpoint} failed (attempt {attempt + 1}): {e}")
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(0.5 * (attempt + 1))  # Exponential backoff
        
        logger.error("All GPU endpoints failed")
        return None
    
    async def get_batch_embeddings(self, texts: List[str], anonymize: bool = True) -> Optional[List[List[float]]]:
        """Get embeddings for multiple texts efficiently"""
        if anonymize:
            texts = [self.anonymize_text(text) for text in texts]
        
        for endpoint in self.endpoints:
            try:
                async with httpx.AsyncClient(timeout=self.timeout * 2) as client:  # Longer timeout for batch
                    response = await client.post(
                        f"{endpoint}/embed/batch",
                        json={"texts": texts},
                        headers={"Content-Type": "application/json"}
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        logger.info(f"Got {data['count']} embeddings from {endpoint}")
                        return data["embeddings"]
                        
            except Exception as e:
                logger.warning(f"Batch request to {endpoint} failed: {e}")
        
        # Fallback to individual requests
        logger.info("Falling back to individual embedding requests")
        embeddings = []
        for text in texts:
            emb = await self.get_embedding(text, anonymize=False)  # Already anonymized
            if emb:
                embeddings.append(emb)
            else:
                return None  # If any fail, return None
        
        return embeddings
    
    async def check_health(self) -> Dict[str, any]:
        """Check health of all GPU endpoints"""
        health_status = {}
        
        for endpoint in self.endpoints:
            try:
                async with httpx.AsyncClient(timeout=2.0) as client:
                    response = await client.get(f"{endpoint}/health")
                    if response.status_code == 200:
                        health_status[endpoint] = response.json()
                    else:
                        health_status[endpoint] = {"status": "unhealthy", "code": response.status_code}
            except Exception as e:
                health_status[endpoint] = {"status": "unreachable", "error": str(e)}
        
        return health_status
    
    def create_product_embedding_text(self, product: Dict, business_type: str) -> str:
        """Create anonymized embedding text for a product"""
        parts = []
        
        # Category and type (safe to include)
        if product.get('category'):
            parts.append(f"Category: {product['category']}")
        if product.get('product_type'):
            parts.append(f"Type: {product['product_type']}")
        
        # Features count (not the actual features)
        if product.get('features'):
            parts.append(f"Features: {len(product['features'])} included")
        
        # Duration (safe for services)
        if product.get('duration'):
            parts.append(f"Duration: {product['duration']}")
        
        # Requirements count (not the actual requirements)
        if product.get('requirements'):
            req_count = 0
            if isinstance(product['requirements'], dict):
                for key, value in product['requirements'].items():
                    if isinstance(value, list):
                        req_count += len(value)
            parts.append(f"Requirements: {req_count} items")
        
        # Tags (generic keywords only)
        if product.get('tags'):
            safe_tags = []
            for tag in product['tags']:
                if not any(char.isdigit() for char in tag) and '@' not in tag:
                    safe_tags.append(tag)
            if safe_tags:
                parts.append(f"Tags: {', '.join(safe_tags[:5])}")  # Limit to 5 tags
        
        return " | ".join(parts)

# Singleton instance
gpu_embedding_client = GPUEmbeddingClient()