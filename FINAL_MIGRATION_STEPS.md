# Final Migration Steps - DO THIS NOW! 🚀

Your RAG system is deployed and ready, but the database table needs to be created. Here are your options:

## Option 1: Railway CLI (Easiest)

```bash
# If you don't have Railway CLI:
npm install -g @railway/cli

# Login and link project:
railway login
railway link

# Run the migration script:
railway run python run_direct_sql.py
```

## Option 2: Direct PostgreSQL Connection

1. Go to your Railway dashboard
2. Click on your PostgreSQL service
3. Click "Connect" → Copy the psql command
4. Run this SQL:

```sql
-- Drop existing table if any
DROP TABLE IF EXISTS menu_embeddings CASCADE;

-- Create the table
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
);

-- Create indexes
CREATE UNIQUE INDEX idx_menu_embeddings_unique 
ON menu_embeddings(restaurant_id, item_id);

CREATE INDEX idx_menu_embeddings_restaurant 
ON menu_embeddings(restaurant_id);
```

## Option 3: Using TablePlus/pgAdmin

Use your database URL from Railway:
- Host: `shortline.proxy.rlwy.net`
- Port: `31808`
- Database: `railway`
- Username: `postgres`
- Password: `pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh`

Then run the SQL above.

## After Migration - Index Your Menu

Once the table is created:

```bash
# Using Railway CLI:
railway run python index_menu_local.py bella_vista_restaurant

# Or use the test script:
railway run python test_index_menu.py
```

## Verify Everything Works

```bash
# Check migration status
curl https://restaurantchat-production.up.railway.app/migration/status

# Test chat with semantic search
curl -X POST https://restaurantchat-production.up.railway.app/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "bella_vista_restaurant",
    "client_id": "550e8400-e29b-41d4-a716-446655440000",
    "sender_type": "client",
    "message": "Show me all your pasta dishes"
  }'
```

## What You'll Get

Once the table is created and menu indexed:
- ✅ "What pasta do you have?" → Lists ALL pasta dishes
- ✅ "Vegetarian options" → Filters correctly
- ✅ "Something healthy" → Understands context
- ✅ "Gluten-free dishes" → Semantic search works

The deployment is ready - just need this one SQL command!