"""
Add pgvector extension and create menu embeddings table
"""
from sqlalchemy import text
from database import engine

def upgrade():
    """Add pgvector extension and create embeddings table"""
    with engine.connect() as conn:
        # Enable pgvector extension
        try:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            conn.commit()
            print("✓ pgvector extension enabled")
        except Exception as e:
            print(f"Note: Could not create pgvector extension: {e}")
            print("This might need superuser privileges. Ask your DB admin to run:")
            print("CREATE EXTENSION vector;")
            return False
        
        # Create menu embeddings table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS menu_embeddings (
                id SERIAL PRIMARY KEY,
                restaurant_id VARCHAR(255) NOT NULL,
                item_id VARCHAR(255) NOT NULL,
                item_name TEXT NOT NULL,
                item_description TEXT,
                item_price VARCHAR(50),
                item_category VARCHAR(100),
                item_ingredients TEXT[],
                dietary_tags TEXT[],
                full_text TEXT NOT NULL,
                embedding vector(384),  -- 384 dimensions for all-MiniLM-L6-v2
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(restaurant_id, item_id)
            )
        """))
        
        # Create index for vector similarity search
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS menu_embeddings_embedding_idx 
            ON menu_embeddings 
            USING ivfflat (embedding vector_cosine_ops)
            WITH (lists = 100)
        """))
        
        # Create index for restaurant_id
        conn.execute(text("""
            CREATE INDEX IF NOT EXISTS menu_embeddings_restaurant_idx 
            ON menu_embeddings(restaurant_id)
        """))
        
        conn.commit()
        print("✓ Menu embeddings table created")
        return True

def downgrade():
    """Remove embeddings table"""
    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS menu_embeddings"))
        conn.commit()
        print("✓ Menu embeddings table removed")

if __name__ == "__main__":
    print("Running pgvector migration...")
    if upgrade():
        print("Migration completed successfully!")
    else:
        print("Migration failed - manual intervention may be required")