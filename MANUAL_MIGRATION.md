# Manual Database Migration Instructions

Since we can't run the migration automatically yet, here are the steps to run it manually:

## Option 1: Railway CLI (Recommended)

```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Run the migration
railway run python run_migrations.py

# Or run Python shell to execute SQL
railway run python
```

Then in Python:
```python
from database import engine
from sqlalchemy import text

with engine.connect() as conn:
    # Enable pgvector
    conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    conn.commit()
    
    # Create table
    conn.execute(text("""
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
            embedding vector(384),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(restaurant_id, item_id)
        )
    """))
    
    # Create indexes
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_menu_embeddings_restaurant 
        ON menu_embeddings(restaurant_id)
    """))
    
    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS idx_menu_embeddings_embedding 
        ON menu_embeddings USING ivfflat (embedding vector_cosine_ops)
    """))
    
    conn.commit()
    print("Migration completed!")
```

## Option 2: Railway PostgreSQL Dashboard

1. Go to your Railway project dashboard
2. Click on your PostgreSQL service
3. Click "Connect" → "psql command"
4. Copy the connection command and run it in your terminal
5. Once connected, run this SQL:

```sql
-- Enable pgvector extension
CREATE EXTENSION IF NOT EXISTS vector;

-- Create menu_embeddings table
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
    embedding vector(384),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(restaurant_id, item_id)
);

-- Create indexes
CREATE INDEX idx_menu_embeddings_restaurant ON menu_embeddings(restaurant_id);
CREATE INDEX idx_menu_embeddings_embedding ON menu_embeddings USING ivfflat (embedding vector_cosine_ops);
```

## Option 3: Using pgAdmin or DBeaver

1. Get your database credentials from Railway:
   - Host: Found in Railway PostgreSQL service
   - Port: Found in Railway PostgreSQL service
   - Database: Found in Railway PostgreSQL service
   - Username: Found in Railway PostgreSQL service
   - Password: Found in Railway PostgreSQL service

2. Connect using pgAdmin or DBeaver
3. Run the SQL commands above

## After Migration

Once the migration is complete, verify it worked:

```bash
curl https://restaurantchat-production.up.railway.app/migration/status
```

Should return:
```json
{
  "pgvector_installed": true,
  "table_exists": true,
  "embedding_count": 0,
  "status": "ready"
}
```

Then you can index your menu items!