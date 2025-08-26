"""
Migration endpoint to add business_type column
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import get_current_owner
import models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/migration", tags=["migration"])

@router.post("/add-business-type")
def run_business_type_migration(
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Add business_type column to restaurants table (admin only).
    """
    if current_admin.restaurant_id not in ["admin", "admin@admin.com"]:
        raise HTTPException(status_code=403, detail="Only admin can run migrations")
    
    try:
        # Check if column exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='restaurants' AND column_name='business_type'
        """))
        
        if result.fetchone():
            return {"status": "success", "message": "business_type column already exists"}
            
        logger.info("Adding business_type column to restaurants table...")
        
        # Add the column
        db.execute(text("""
            ALTER TABLE restaurants 
            ADD COLUMN business_type VARCHAR DEFAULT 'restaurant'
        """))
        
        # Update existing restaurants based on their data
        db.execute(text("""
            UPDATE restaurants 
            SET business_type = COALESCE(
                CAST(data->>'business_type' AS VARCHAR),
                'restaurant'
            )
            WHERE business_type IS NULL
        """))
        
        db.commit()
        logger.info("Successfully added business_type column")
        
        return {"status": "success", "message": "Successfully added business_type column"}
        
    except Exception as e:
        logger.error(f"Error adding business_type column: {str(e)}")
        db.rollback()
        return {"status": "error", "message": f"Migration failed: {str(e)}"}