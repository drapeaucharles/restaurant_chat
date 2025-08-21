#!/usr/bin/env python3
"""
Safe migration script to convert restaurant system to universal business system
Can be run multiple times safely
"""
import logging
from sqlalchemy import text
from database import SessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run safe migration to universal business system"""
    db = SessionLocal()
    
    try:
        # 1. Check if we already have the new structure
        check_businesses = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'businesses'
            );
        """)
        has_businesses = db.execute(check_businesses).scalar()
        
        if not has_businesses:
            logger.info("Creating businesses table from restaurants...")
            
            # Create businesses table as copy of restaurants
            db.execute(text("""
                CREATE TABLE businesses AS 
                SELECT 
                    restaurant_id AS business_id,
                    password,
                    role,
                    data,
                    whatsapp_number,
                    whatsapp_session_id,
                    restaurant_category AS business_category,
                    rag_mode,
                    'restaurant'::varchar(50) AS business_type,
                    '{}'::jsonb AS metadata
                FROM restaurants;
                
                -- Add primary key
                ALTER TABLE businesses ADD PRIMARY KEY (business_id);
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_businesses_type ON businesses(business_type);
            """))
            logger.info("✅ Created businesses table")
        else:
            logger.info("ℹ️  Businesses table already exists")
        
        # 2. Add columns if they don't exist
        columns_to_add = [
            ("businesses", "business_type", "VARCHAR(50) DEFAULT 'restaurant'"),
            ("businesses", "metadata", "JSONB DEFAULT '{}'")
        ]
        
        for table, column, definition in columns_to_add:
            try:
                db.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {column} {definition}"))
                logger.info(f"✅ Added column {column} to {table}")
            except Exception as e:
                logger.info(f"ℹ️  Column {column} already exists in {table}")
        
        # 3. Check if products table exists
        check_products = text("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_name = 'products'
            );
        """)
        has_products = db.execute(check_products).scalar()
        
        if not has_products:
            logger.info("Creating products table from menu_items...")
            
            # Create products table
            db.execute(text("""
                CREATE TABLE products AS 
                SELECT 
                    id,
                    restaurant_id AS business_id,
                    name,
                    description,
                    price,
                    category,
                    'menu_item'::varchar(50) AS product_type,
                    NULL::varchar(100) AS duration,
                    NULL::jsonb AS requirements,
                    NULL::jsonb AS features,
                    COALESCE(allergens, '[]'::jsonb) AS tags,
                    true AS available,
                    NULL::varchar AS image_url,
                    name_embedding,
                    description_embedding,
                    tags_embedding,
                    combined_embedding
                FROM menu_items;
                
                -- Add primary key
                ALTER TABLE products ADD PRIMARY KEY (id);
                
                -- Create indexes
                CREATE INDEX IF NOT EXISTS idx_products_business ON products(business_id);
                CREATE INDEX IF NOT EXISTS idx_products_type ON products(business_id, product_type);
                
                -- Add foreign key
                ALTER TABLE products 
                ADD CONSTRAINT products_business_id_fkey 
                FOREIGN KEY (business_id) REFERENCES businesses(business_id);
            """))
            logger.info("✅ Created products table")
        else:
            logger.info("ℹ️  Products table already exists")
        
        # 4. Add new columns to products if they don't exist
        product_columns = [
            ("product_type", "VARCHAR(50) DEFAULT 'menu_item'"),
            ("duration", "VARCHAR(100)"),
            ("requirements", "JSONB"),
            ("features", "JSONB"),
            ("tags", "JSONB DEFAULT '[]'"),
            ("available", "BOOLEAN DEFAULT true"),
            ("image_url", "VARCHAR")
        ]
        
        for column, definition in product_columns:
            try:
                db.execute(text(f"ALTER TABLE products ADD COLUMN IF NOT EXISTS {column} {definition}"))
                logger.info(f"✅ Added column {column} to products")
            except Exception as e:
                logger.info(f"ℹ️  Column {column} already exists in products")
        
        # 5. Create backward compatibility views
        logger.info("Creating compatibility views...")
        
        db.execute(text("""
            CREATE OR REPLACE VIEW restaurants AS 
            SELECT 
                business_id AS restaurant_id,
                password,
                role,
                data,
                whatsapp_number,
                whatsapp_session_id,
                business_category AS restaurant_category,
                rag_mode
            FROM businesses 
            WHERE business_type = 'restaurant';
        """))
        
        db.execute(text("""
            CREATE OR REPLACE VIEW menu_items AS 
            SELECT 
                id,
                business_id AS restaurant_id,
                name,
                description,
                price,
                category,
                tags AS allergens,
                name_embedding,
                description_embedding,
                tags_embedding,
                combined_embedding
            FROM products 
            WHERE product_type = 'menu_item';
        """))
        
        logger.info("✅ Created compatibility views")
        
        # 6. Update clients table to use business_id
        try:
            db.execute(text("""
                ALTER TABLE clients 
                RENAME COLUMN restaurant_id TO business_id;
            """))
            logger.info("✅ Renamed restaurant_id to business_id in clients")
        except Exception:
            logger.info("ℹ️  Clients table already uses business_id")
        
        # 7. Update chat_messages table
        try:
            db.execute(text("""
                ALTER TABLE chat_messages 
                RENAME COLUMN restaurant_id TO business_id;
            """))
            logger.info("✅ Renamed restaurant_id to business_id in chat_messages")
        except Exception:
            logger.info("ℹ️  Chat_messages table already uses business_id")
        
        # Commit all changes
        db.commit()
        
        logger.info("\n🎉 Migration complete!")
        logger.info("The system now supports multiple business types while maintaining backward compatibility.")
        logger.info("\nNext steps:")
        logger.info("1. Run setup_legal_business.py to add a legal/visa agency")
        logger.info("2. Update your code to use models_universal.py")
        logger.info("3. Test with both restaurant and legal service queries")
        
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()

if __name__ == "__main__":
    run_migration()