"""
Add business_type column to restaurants table
"""
from sqlalchemy import text
from database import SessionLocal
import logging

logger = logging.getLogger(__name__)

def add_business_type_column():
    """Add business_type column to restaurants table if it doesn't exist"""
    db = SessionLocal()
    try:
        # Check if column already exists
        result = db.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='restaurants' AND column_name='business_type'
        """))
        
        if not result.fetchone():
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
                    data->>'business_type',
                    'restaurant'
                )
                WHERE business_type IS NULL
            """))
            
            db.commit()
            logger.info("Successfully added business_type column")
        else:
            logger.info("business_type column already exists")
            
    except Exception as e:
        logger.error(f"Error adding business_type column: {str(e)}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    add_business_type_column()