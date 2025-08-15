# 📍 WHERE TO FIND THE QUERY TAB IN RAILWAY

## Step-by-Step Guide:

### 1. Go to Railway Dashboard
   - URL: https://railway.app/dashboard
   - Login if needed

### 2. Find Your Project
   - Look for your restaurant project
   - It should show multiple services (your app + PostgreSQL)

### 3. Click on PostgreSQL Service
   - Look for the **PostgreSQL** box/card
   - It usually has a database icon 🗄️
   - Click on it

### 4. Find the Query Tab
   Once you're in the PostgreSQL service, you'll see tabs at the top:
   - **Overview**
   - **Variables** 
   - **Settings**
   - **Data** ← Click this one!

### 5. Inside the Data Tab
   You'll see:
   - **Connect** - Connection strings
   - **Query** ← This is what you want!
   - **Tables** - List of tables

### 6. In the Query Section
   - There's a text box where you can type SQL
   - Paste this SQL:

```sql
-- Fix transaction and create table
ROLLBACK;

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
CREATE UNIQUE INDEX idx_menu_embeddings_unique ON menu_embeddings(restaurant_id, item_id);
CREATE INDEX idx_menu_embeddings_restaurant ON menu_embeddings(restaurant_id);

-- Verify
SELECT 'SUCCESS! Table created' as status;
```

### 7. Click "Run Query"
   - There should be a button to execute the query
   - Click it and wait for results

## Alternative: If You Can't Find It

Use any PostgreSQL client with this connection string:
```
postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway
```

Popular clients:
- **pgAdmin** (free)
- **TablePlus** (free trial)
- **DBeaver** (free)
- **Postico** (Mac)

## Visual Guide:
```
Railway Dashboard
    └── Your Project
        └── PostgreSQL Service (click this)
            └── Data Tab (click this)
                └── Query Section (paste SQL here)
                    └── Run Query Button
```

That's where you run the SQL!