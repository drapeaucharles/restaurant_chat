# 🚨 IMMEDIATE ACTION NEEDED!

The RAG system is deployed but waiting for the database table. Here's the quickest way to fix it:

## Option 1: Copy & Paste (30 seconds)

1. Go to Railway Dashboard → PostgreSQL → Query
2. Paste this SQL and run it:

```sql
CREATE TABLE IF NOT EXISTS menu_embeddings (
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(restaurant_id, item_id)
);

CREATE INDEX IF NOT EXISTS idx_menu_embeddings_restaurant 
ON menu_embeddings(restaurant_id);
```

## Option 2: Railway CLI (1 minute)

```bash
# One command:
railway run psql -f CREATE_TABLE_NOW.sql
```

## Option 3: Direct Connection

Connect with these credentials:
```
postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway
```

Then run the SQL above.

## After Table Creation

Test that it worked:
```bash
curl https://restaurantchat-production.up.railway.app/migration/status
```

Should show: `"table_exists": true`

Then your chat will work with full RAG capabilities!

**The entire system is ready - just needs this one table!**