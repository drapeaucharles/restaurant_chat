"""
Database debug endpoints
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/db-debug", tags=["debug"])

@router.get("/check-structure")
def check_database_structure(db: Session = Depends(get_db)):
    """Check database structure for restaurants"""
    try:
        results = {}
        
        # Check if restaurants is a table or view
        table_check = db.execute(text("""
            SELECT table_name, table_type 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_name LIKE '%restaurant%'
            ORDER BY table_name
        """))
        
        results["tables"] = [{"name": row[0], "type": row[1]} for row in table_check]
        
        # Get columns for each table
        for table_info in results["tables"]:
            table_name = table_info["name"]
            columns = db.execute(text(f"""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = '{table_name}'
                ORDER BY ordinal_position
            """))
            table_info["columns"] = [
                {"name": col[0], "type": col[1], "default": col[2]} 
                for col in columns
            ]
        
        # Get view definitions if any
        views = db.execute(text("""
            SELECT viewname, definition 
            FROM pg_views 
            WHERE schemaname = 'public' 
            AND viewname LIKE '%restaurant%'
        """))
        
        results["views"] = [{"name": row[0], "definition": row[1]} for row in views]
        
        return results
        
    except Exception as e:
        return {"error": str(e)}

@router.post("/add-business-type-to-base")
def add_business_type_to_base(db: Session = Depends(get_db)):
    """Add business_type column to the actual table"""
    try:
        # Find the actual table (not view)
        tables = db.execute(text("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public' 
            AND table_type = 'BASE TABLE'
            AND table_name LIKE '%restaurant%'
        """))
        
        base_tables = [row[0] for row in tables]
        
        if not base_tables:
            return {"error": "No base restaurant table found"}
        
        results = []
        for table_name in base_tables:
            # Check if column exists
            check = db.execute(text(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table_name}' 
                AND column_name = 'business_type'
            """))
            
            if check.fetchone():
                results.append({"table": table_name, "status": "column already exists"})
            else:
                try:
                    # Add the column
                    db.execute(text(f"""
                        ALTER TABLE {table_name} 
                        ADD COLUMN business_type VARCHAR DEFAULT 'restaurant'
                    """))
                    db.commit()
                    results.append({"table": table_name, "status": "column added successfully"})
                except Exception as e:
                    db.rollback()
                    results.append({"table": table_name, "status": f"error: {str(e)}"})
        
        return {"results": results, "base_tables": base_tables}
        
    except Exception as e:
        db.rollback()
        return {"error": str(e)}