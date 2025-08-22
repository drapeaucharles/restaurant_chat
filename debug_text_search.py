#!/usr/bin/env python3
"""Debug endpoint for text search"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from services.text_search_service import text_search_service
from services.embedding_service_universal import universal_embedding_service
from pydantic import BaseModel

router = APIRouter()

class SearchDebugRequest(BaseModel):
    business_id: str
    query: str

@router.post("/debug/search")
def debug_search(req: SearchDebugRequest, db: Session = Depends(get_db)):
    """Debug text search functionality"""
    
    # Check if ML is available
    ml_available = universal_embedding_service.model is not None
    
    # Try text search directly
    text_results = text_search_service.search_products(
        db, req.business_id, req.query, limit=5
    )
    
    # Try embedding search
    embedding_results = []
    try:
        embedding_results = universal_embedding_service.search_similar_items(
            db, req.business_id, req.query, limit=5
        )
    except Exception as e:
        embedding_error = str(e)
    else:
        embedding_error = None
    
    return {
        "ml_available": ml_available,
        "query": req.query,
        "text_search_results": text_results,
        "embedding_search_results": embedding_results,
        "embedding_error": embedding_error
    }