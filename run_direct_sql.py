#!/usr/bin/env python3
"""
Run SQL directly using SQLAlchemy
"""
from database import engine
from sqlalchemy import text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run migration directly"""
    with engine.connect() as conn:
        try:
            # Drop table if exists
            logger.info("Dropping existing table...")
            conn.execute(text("DROP TABLE IF EXISTS menu_embeddings CASCADE"))
            conn.commit()
            
            # Create new table
            logger.info("Creating menu_embeddings table...")
            conn.execute(text("""
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
            """))
            conn.commit()
            
            # Create indexes
            logger.info("Creating indexes...")
            conn.execute(text("""
                CREATE UNIQUE INDEX idx_menu_embeddings_unique 
                ON menu_embeddings(restaurant_id, item_id)
            """))
            
            conn.execute(text("""
                CREATE INDEX idx_menu_embeddings_restaurant 
                ON menu_embeddings(restaurant_id)
            """))
            conn.commit()
            
            # Verify table exists
            result = conn.execute(text("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_name = 'menu_embeddings'
            """))
            exists = result.scalar() > 0
            
            logger.info(f"Table exists: {exists}")
            
            if exists:
                print("\n✅ Migration completed successfully!")
                print("   Table 'menu_embeddings' created")
                print("   Ready for indexing menu items")
            else:
                print("\n❌ Migration failed - table not created")
                
        except Exception as e:
            logger.error(f"Migration error: {e}")
            conn.rollback()
            raise

if __name__ == "__main__":
    print("🔧 Running direct SQL migration...")
    print("   Using database from .env file")
    print("=" * 50)
    
    try:
        run_migration()
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\nPlease run this on Railway:")
        print("railway run python run_direct_sql.py")