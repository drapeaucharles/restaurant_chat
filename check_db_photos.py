import os
from sqlalchemy import create_engine, text
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Get database URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    print("DATABASE_URL not found in environment")
    exit(1)

# Create engine
engine = create_engine(DATABASE_URL)

# Query the restaurant data
with engine.connect() as conn:
    result = conn.execute(
        text("SELECT restaurant_id, data FROM restaurants WHERE restaurant_id = :rid"),
        {"rid": "bella_vista_restaurant"}
    )
    
    row = result.fetchone()
    if row:
        restaurant_id, data = row
        print(f"Restaurant ID: {restaurant_id}")
        print(f"Data type: {type(data)}")
        
        # Parse JSON data
        if isinstance(data, str):
            restaurant_data = json.loads(data)
        else:
            restaurant_data = data
            
        menu = restaurant_data.get("menu", [])
        print(f"\nTotal menu items: {len(menu)}")
        
        # Check first 5 items
        print("\nFirst 5 menu items:")
        for i, item in enumerate(menu[:5]):
            print(f"\nItem {i+1}: {item.get('title') or item.get('dish')}")
            print(f"  Has photo_url: {'photo_url' in item}")
            if 'photo_url' in item:
                print(f"  Photo URL: {item['photo_url']}")
        
        # Count items with photo_url
        items_with_photos = sum(1 for item in menu if 'photo_url' in item and item['photo_url'])
        print(f"\n\nTotal items with photo_url: {items_with_photos} out of {len(menu)}")
    else:
        print("Restaurant not found")