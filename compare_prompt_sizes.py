#!/usr/bin/env python3
"""Compare prompt sizes between full_menu and db_query services"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import models
from schemas.chat import ChatRequest

# Setup database
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway')
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
db = SessionLocal()

# Test request
test_request = ChatRequest(
    restaurant_id="bella_vista_restaurant",
    client_id="550e8400-e29b-41d4-a716-446655440099",
    sender_type="client",
    message="I like tomato"
)

print("Comparing prompt sizes for: 'I like tomato'")
print("=" * 60)

# Get restaurant data
restaurant = db.query(models.Restaurant).filter(
    models.Restaurant.restaurant_id == test_request.restaurant_id
).first()

menu_items = restaurant.data.get('menu', []) if restaurant and restaurant.data else []
print(f"\nTotal menu items: {len(menu_items)}")

# 1. Full Menu Service prompt size
from services.mia_chat_service_full_menu import mia_chat_service_full_menu

# Mock the service to capture prompt
original_get_mia = None
captured_prompts = {}

def capture_prompt(service_name):
    def mock_mia(prompt, params):
        captured_prompts[service_name] = prompt
        return "Mock response"
    return mock_mia

# Capture full_menu prompt
import services.mia_chat_service_full_menu
original_get_mia = services.mia_chat_service_full_menu.get_mia_response_hybrid
services.mia_chat_service_full_menu.get_mia_response_hybrid = capture_prompt("full_menu")

try:
    mia_chat_service_full_menu(test_request, db)
except:
    pass

# Restore
services.mia_chat_service_full_menu.get_mia_response_hybrid = original_get_mia

# 2. DB Query Service prompt size
from services.mia_chat_service_db_query import mia_chat_service_db_query, search_dishes_by_ingredient

# Get what db_query would fetch for "I like tomato"
tomato_dishes = search_dishes_by_ingredient(db, test_request.restaurant_id, "tomato")
print(f"\nDB Query found {len(tomato_dishes)} tomato dishes")

# Capture db_query prompt
import services.mia_chat_service_db_query
original_get_mia = services.mia_chat_service_db_query.get_mia_response_hybrid
services.mia_chat_service_db_query.get_mia_response_hybrid = capture_prompt("db_query")
services.mia_chat_service_db_query.USE_FAST_POLLING = False  # Use standard polling

try:
    mia_chat_service_db_query(test_request, db)
except:
    pass

# Restore
services.mia_chat_service_db_query.get_mia_response_hybrid = original_get_mia

# Compare results
print("\n" + "=" * 60)
print("PROMPT SIZE COMPARISON:")
print("=" * 60)

for service, prompt in captured_prompts.items():
    if prompt:
        lines = prompt.count('\n')
        chars = len(prompt)
        
        # Count menu items in prompt
        menu_count = prompt.count('$')  # Rough count of price mentions
        
        print(f"\n{service.upper()} Service:")
        print(f"  - Total characters: {chars:,}")
        print(f"  - Total lines: {lines}")
        print(f"  - Approximate menu items sent: {menu_count}")
        
        # Show first 500 chars
        print(f"  - Preview: {prompt[:500]}...")

# Calculate difference
if "full_menu" in captured_prompts and "db_query" in captured_prompts:
    full_chars = len(captured_prompts["full_menu"])
    db_chars = len(captured_prompts["db_query"])
    reduction = (1 - db_chars/full_chars) * 100
    
    print(f"\n" + "=" * 60)
    print(f"DB_QUERY REDUCES PROMPT SIZE BY: {reduction:.1f}%")
    print(f"Characters saved: {full_chars - db_chars:,}")

db.close()