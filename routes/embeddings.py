"""
Endpoints for managing embeddings and RAG functionality
"""
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import get_current_restaurant
import models
from services.embedding_service import embedding_service
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/embeddings", tags=["embeddings"])

@router.post("/index/{restaurant_id}")
async def index_restaurant_menu(
    restaurant_id: str,
    background_tasks: BackgroundTasks,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """Index menu items for a restaurant to enable RAG search"""
    
    # Verify authorization
    if current_restaurant.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail="Not authorized to index this restaurant")
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        raise HTTPException(status_code=404, detail="Restaurant not found")
    
    # Get menu items
    data = restaurant.data or {}
    menu_items = data.get("menu", [])
    
    if not menu_items:
        return {
            "status": "error",
            "message": "No menu items found to index"
        }
    
    # Index in background
    background_tasks.add_task(
        embedding_service.index_restaurant_menu,
        db,
        restaurant_id,
        menu_items
    )
    
    return {
        "status": "started",
        "message": f"Indexing {len(menu_items)} menu items in background",
        "restaurant_id": restaurant_id
    }

@router.get("/status/{restaurant_id}")
async def get_embedding_status(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """Get embedding status for a restaurant"""
    
    # Verify authorization
    if current_restaurant.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Count embeddings
    result = db.execute(text("""
        SELECT 
            COUNT(*) as total_items,
            COUNT(embedding) as indexed_items,
            MAX(created_at) as last_indexed,
            MIN(created_at) as first_indexed
        FROM menu_embeddings
        WHERE restaurant_id = :restaurant_id
    """), {"restaurant_id": restaurant_id}).first()
    
    return {
        "restaurant_id": restaurant_id,
        "total_items": result.total_items,
        "indexed_items": result.indexed_items,
        "last_indexed": result.last_indexed,
        "first_indexed": result.first_indexed,
        "is_indexed": result.indexed_items > 0
    }

@router.post("/search")
async def search_menu_items(
    query: str,
    restaurant_id: str,
    limit: int = 5,
    db: Session = Depends(get_db)
):
    """Search menu items using semantic search"""
    
    # Check if restaurant has embeddings
    count = db.execute(text("""
        SELECT COUNT(*) FROM menu_embeddings WHERE restaurant_id = :restaurant_id
    """), {"restaurant_id": restaurant_id}).scalar()
    
    if count == 0:
        return {
            "status": "error",
            "message": "No embeddings found. Please index the menu first.",
            "results": []
        }
    
    # Search
    results = embedding_service.search_similar_items(
        db=db,
        restaurant_id=restaurant_id,
        query=query,
        limit=limit
    )
    
    return {
        "status": "success",
        "query": query,
        "results": results,
        "count": len(results)
    }

@router.delete("/clear/{restaurant_id}")
async def clear_embeddings(
    restaurant_id: str,
    current_restaurant: models.Restaurant = Depends(get_current_restaurant),
    db: Session = Depends(get_db)
):
    """Clear all embeddings for a restaurant"""
    
    # Verify authorization
    if current_restaurant.restaurant_id != restaurant_id:
        raise HTTPException(status_code=403, detail="Not authorized")
    
    # Delete embeddings
    result = db.execute(text("""
        DELETE FROM menu_embeddings WHERE restaurant_id = :restaurant_id
    """), {"restaurant_id": restaurant_id})
    
    db.commit()
    
    return {
        "status": "success",
        "deleted": result.rowcount,
        "restaurant_id": restaurant_id
    }

@router.get("/stats")
async def get_embedding_stats(db: Session = Depends(get_db)):
    """Get global embedding statistics"""
    
    result = db.execute(text("""
        SELECT 
            COUNT(DISTINCT restaurant_id) as restaurants_indexed,
            COUNT(*) as total_items,
            pg_size_pretty(pg_relation_size('menu_embeddings')) as table_size
        FROM menu_embeddings
    """)).first()
    
    return {
        "restaurants_indexed": result.restaurants_indexed,
        "total_items": result.total_items,
        "table_size": result.table_size,
        "embedding_model": "all-MiniLM-L6-v2",
        "embedding_dimensions": 384
    }