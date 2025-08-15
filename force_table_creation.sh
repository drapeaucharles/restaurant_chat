#!/bin/bash
# Force table creation script

echo "🔧 Force creating table via Railway CLI..."
echo ""
echo "Please run these commands:"
echo ""
echo "1. Install Railway CLI (if not installed):"
echo "   npm install -g @railway/cli"
echo ""
echo "2. Login and link:"
echo "   railway login"
echo "   railway link"
echo ""
echo "3. Create the table (copy this entire command):"
cat << 'EOF'
railway run psql -c "DROP TABLE IF EXISTS menu_embeddings CASCADE; CREATE TABLE menu_embeddings (id SERIAL PRIMARY KEY, restaurant_id VARCHAR(255) NOT NULL, item_id VARCHAR(255) NOT NULL, item_name VARCHAR(255) NOT NULL, item_description TEXT, item_price VARCHAR(50), item_category VARCHAR(100), item_ingredients TEXT, dietary_tags TEXT, full_text TEXT NOT NULL, embedding_json TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP); CREATE UNIQUE INDEX idx_menu_embeddings_unique ON menu_embeddings(restaurant_id, item_id); CREATE INDEX idx_menu_embeddings_restaurant ON menu_embeddings(restaurant_id);"
EOF

echo ""
echo "4. Verify it worked:"
echo '   railway run psql -c "SELECT count(*) FROM menu_embeddings;"'
echo ""
echo "Should return: count = 0"