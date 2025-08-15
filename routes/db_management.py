"""
Database management endpoints for emergency operations
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel
import os
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/db-manage", tags=["database-management"])

class SQLCommand(BaseModel):
    sql: str
    secret_key: str

@router.post("/execute-sql")
async def execute_sql(
    command: SQLCommand,
    db: Session = Depends(get_db)
):
    """Execute SQL command - requires secret key"""
    
    # Simple authentication
    expected_key = os.getenv("DB_MANAGEMENT_KEY", "emergency-db-key-2024")
    if command.secret_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    # Safety check - only allow specific operations
    sql_lower = command.sql.lower()
    allowed_operations = ['create table', 'drop table if exists', 'select', 'create index', 'create unique index']
    
    if not any(op in sql_lower for op in allowed_operations):
        raise HTTPException(status_code=400, detail="Operation not allowed")
    
    # Prevent dangerous operations
    if any(danger in sql_lower for danger in ['delete from', 'truncate', 'drop database', 'drop schema']):
        raise HTTPException(status_code=400, detail="Dangerous operation blocked")
    
    try:
        # Execute SQL
        result = db.execute(text(command.sql))
        
        # Handle different types of results
        if sql_lower.startswith('select'):
            # Fetch results for SELECT queries
            rows = result.fetchall()
            columns = result.keys()
            
            # Convert to list of dicts
            data = []
            for row in rows[:100]:  # Limit to 100 rows
                data.append(dict(zip(columns, row)))
            
            return {
                "status": "success",
                "rows_returned": len(data),
                "data": data
            }
        else:
            # For DDL commands
            db.commit()
            return {
                "status": "success",
                "message": f"Command executed successfully",
                "rows_affected": result.rowcount if hasattr(result, 'rowcount') else 0
            }
            
    except Exception as e:
        db.rollback()
        logger.error(f"SQL execution error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Command failed"
        }

@router.post("/create-menu-embeddings-table")
async def create_menu_embeddings_table(
    secret_key: str,
    db: Session = Depends(get_db)
):
    """Create menu_embeddings table directly"""
    
    # Simple authentication
    expected_key = os.getenv("DB_MANAGEMENT_KEY", "emergency-db-key-2024")
    if secret_key != expected_key:
        raise HTTPException(status_code=403, detail="Invalid secret key")
    
    try:
        # Drop existing table
        db.execute(text("DROP TABLE IF EXISTS menu_embeddings CASCADE"))
        db.commit()
        
        # Create table
        create_sql = """
        CREATE TABLE menu_embeddings (
            id SERIAL PRIMARY KEY,
            restaurant_id VARCHAR(255) NOT NULL,
            item_id VARCHAR(255) NOT NULL,
            item_name VARCHAR(255) NOT NULL,
            item_description TEXT,
            item_price VARCHAR(50),
            item_category VARCHAR(100),
            item_ingredients TEXT,
            dietary_tags TEXT,
            full_text TEXT NOT NULL,
            embedding_json TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
        db.execute(text(create_sql))
        db.commit()
        
        # Create indexes
        db.execute(text("""
            CREATE UNIQUE INDEX idx_menu_embeddings_unique 
            ON menu_embeddings(restaurant_id, item_id)
        """))
        
        db.execute(text("""
            CREATE INDEX idx_menu_embeddings_restaurant 
            ON menu_embeddings(restaurant_id)
        """))
        db.commit()
        
        # Verify
        result = db.execute(text("SELECT COUNT(*) FROM menu_embeddings"))
        count = result.scalar()
        
        return {
            "status": "success",
            "message": "Table created successfully",
            "table_exists": True,
            "row_count": count
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Table creation error: {e}")
        return {
            "status": "error",
            "error": str(e),
            "message": "Failed to create table"
        }

@router.get("/check-tables")
async def check_tables(db: Session = Depends(get_db)):
    """Check which tables exist"""
    
    try:
        result = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            ORDER BY table_name
        """))
        
        tables = [row[0] for row in result]
        
        # Check specifically for menu_embeddings
        has_menu_embeddings = 'menu_embeddings' in tables
        
        return {
            "status": "success",
            "tables": tables,
            "has_menu_embeddings": has_menu_embeddings,
            "total_tables": len(tables)
        }
        
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
            "tables": []
        }