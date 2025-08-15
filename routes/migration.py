"""
Database migration endpoints
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_restaurant
import models
import logging
import os

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/migration", tags=["migration"])

from pydantic import BaseModel

class MigrationRequest(BaseModel):
    secret_key: str

@router.post("/run-pgvector")
async def run_pgvector_migration(
    request: MigrationRequest,
    db: Session = Depends(get_db)
):
    """Run pgvector migration - requires secret key"""
    
    # Simple authentication
    expected_key = os.getenv("MIGRATION_SECRET_KEY", "your-secret-migration-key")
    if request.secret_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    try:
        # Check if pgvector extension exists
        result = db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        has_vector = result.scalar() is not None
        
        if not has_vector:
            # Try to create extension
            db.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            db.commit()
            logger.info("Created pgvector extension")
        
        # Create menu_embeddings table without vector column
        db.execute(text("""
            CREATE TABLE IF NOT EXISTS menu_embeddings (
                id SERIAL PRIMARY KEY,
                restaurant_id VARCHAR(255) NOT NULL,
                item_id VARCHAR(255) NOT NULL,
                item_name VARCHAR(255) NOT NULL,
                item_description TEXT,
                item_price VARCHAR(50),
                item_category VARCHAR(100),
                item_ingredients JSONB,
                dietary_tags JSONB,
                full_text TEXT NOT NULL,
                embedding_json TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(restaurant_id, item_id)
            )
        """))
        
        # Create indexes
        db.execute(text("""
            CREATE INDEX IF NOT EXISTS idx_menu_embeddings_restaurant 
            ON menu_embeddings(restaurant_id)
        """))
        
        # Skip vector index since we're using JSON storage
        logger.info("Skipping vector index (using JSON storage)")
        
        db.commit()
        
        # Check if table was created
        result = db.execute(text("""
            SELECT COUNT(*) FROM information_schema.tables 
            WHERE table_name = 'menu_embeddings'
        """))
        table_exists = result.scalar() > 0
        
        return {
            "status": "success",
            "message": "Migration completed successfully",
            "pgvector_installed": True,
            "table_created": table_exists
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Migration failed: {str(e)}")
        
        # If pgvector not available, return helpful message
        if "vector" in str(e).lower():
            return {
                "status": "partial",
                "message": "Table created but pgvector extension not available",
                "error": str(e),
                "suggestion": "Contact Railway support to enable pgvector extension"
            }
        
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def check_migration_status(db: Session = Depends(get_db)):
    """Check migration status"""
    
    try:
        # Check pgvector
        result = db.execute(text("SELECT 1 FROM pg_extension WHERE extname = 'vector'"))
        has_vector = result.scalar() is not None
        
        # Check table - try direct query first
        has_table = False
        try:
            result = db.execute(text("SELECT 1 FROM menu_embeddings LIMIT 1"))
            has_table = True  # If query succeeds, table exists
        except:
            # Fallback to information_schema
            try:
                result = db.execute(text("""
                    SELECT COUNT(*) FROM information_schema.tables 
                    WHERE table_name = 'menu_embeddings'
                """))
                has_table = result.scalar() > 0
            except:
                has_table = False
        
        # Count embeddings if table exists
        embedding_count = 0
        if has_table:
            result = db.execute(text("SELECT COUNT(*) FROM menu_embeddings"))
            embedding_count = result.scalar()
        
        return {
            "pgvector_installed": has_vector,
            "table_exists": has_table,
            "embedding_count": embedding_count,
            "status": "ready" if has_vector and has_table else "pending"
        }
        
    except Exception as e:
        return {
            "pgvector_installed": False,
            "table_exists": False,
            "embedding_count": 0,
            "status": "error",
            "error": str(e)
        }