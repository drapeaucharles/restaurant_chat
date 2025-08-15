#!/usr/bin/env python3
"""
Emergency table creation using project's database module
"""
import os
import sys

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set environment variable
os.environ['DATABASE_URL'] = 'postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway'

print("🚨 Emergency table creation...")

try:
    # Import after setting env
    from database import engine
    from sqlalchemy import text, MetaData, Table, Column, Integer, String, Text, TIMESTAMP, func
    from sqlalchemy.schema import CreateTable, CreateIndex
    
    print("✅ Connected to database")
    
    # Create metadata
    metadata = MetaData()
    
    # Define table
    menu_embeddings = Table('menu_embeddings', metadata,
        Column('id', Integer, primary_key=True, autoincrement=True),
        Column('restaurant_id', String(255), nullable=False),
        Column('item_id', String(255), nullable=False),
        Column('item_name', String(255), nullable=False),
        Column('item_description', Text),
        Column('item_price', String(50)),
        Column('item_category', String(100)),
        Column('item_ingredients', Text),
        Column('dietary_tags', Text),
        Column('full_text', Text, nullable=False),
        Column('embedding_json', Text),
        Column('created_at', TIMESTAMP, server_default=func.current_timestamp()),
        Column('updated_at', TIMESTAMP, server_default=func.current_timestamp())
    )
    
    # Execute
    with engine.begin() as conn:
        # Drop if exists
        conn.execute(text("DROP TABLE IF EXISTS menu_embeddings CASCADE"))
        print("✅ Dropped old table")
        
        # Create table
        conn.execute(CreateTable(menu_embeddings))
        print("✅ Created table")
        
        # Create indexes
        conn.execute(text("""
            CREATE UNIQUE INDEX idx_menu_embeddings_unique 
            ON menu_embeddings(restaurant_id, item_id)
        """))
        conn.execute(text("""
            CREATE INDEX idx_menu_embeddings_restaurant 
            ON menu_embeddings(restaurant_id)
        """))
        print("✅ Created indexes")
        
        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM menu_embeddings"))
        count = result.scalar()
        print(f"✅ Table exists with {count} rows")
        
        # Get columns
        result = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'menu_embeddings'
            ORDER BY ordinal_position
        """))
        columns = [row[0] for row in result]
        print(f"✅ Columns: {', '.join(columns)}")
    
    print("\n🎉 SUCCESS! Table created!")
    print("Now you can:")
    print("1. Test the chat endpoint")
    print("2. Index menu items")
    
    # Test API
    import requests
    response = requests.get("https://restaurantchat-production.up.railway.app/migration/status")
    if response.status_code == 200:
        print(f"\n📊 API Status: {response.json()}")
        
except Exception as e:
    print(f"\n❌ Error: {e}")
    import traceback
    traceback.print_exc()
    
    print("\n📝 Please run manually:")
    print("railway run python emergency_create_table.py")