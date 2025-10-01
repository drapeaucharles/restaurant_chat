#!/usr/bin/env python3
"""
Script to add pizza items to the restaurant database.
This addresses the pizza inconsistency issue by adding proper pizza items.
"""

import requests
import json
import uuid

# Pizza items to add to the restaurant menu
PIZZA_ITEMS = [
    {
        "title": "Margherita Pizza",
        "description": "Classic Italian pizza with fresh mozzarella, tomato sauce, and basil",
        "price": "14.99",
        "ingredients": ["tomato sauce", "mozzarella", "fresh basil", "olive oil"],
        "allergens": ["dairy", "gluten"],
        "restaurant_category": "Pizza",
        "is_vegetarian": True,
        "is_vegan": False,
        "is_gluten_free": False,
        "is_dairy_free": False,
        "is_nut_free": True
    },
    {
        "title": "Pepperoni Pizza",
        "description": "Traditional pizza topped with spicy pepperoni and mozzarella cheese",
        "price": "16.99",
        "ingredients": ["tomato sauce", "mozzarella", "pepperoni", "oregano"],
        "allergens": ["dairy", "gluten", "pork"],
        "restaurant_category": "Pizza",
        "is_vegetarian": False,
        "is_vegan": False,
        "is_gluten_free": False,
        "is_dairy_free": False,
        "is_nut_free": True
    },
    {
        "title": "Quattro Stagioni Pizza",
        "description": "Four seasons pizza with artichokes, mushrooms, prosciutto, and olives",
        "price": "18.99",
        "ingredients": ["tomato sauce", "mozzarella", "artichokes", "mushrooms", "prosciutto", "olives"],
        "allergens": ["dairy", "gluten", "pork"],
        "restaurant_category": "Pizza",
        "is_vegetarian": False,
        "is_vegan": False,
        "is_gluten_free": False,
        "is_dairy_free": False,
        "is_nut_free": True
    },
    {
        "title": "Vegetarian Supreme Pizza",
        "description": "Loaded with bell peppers, onions, mushrooms, olives, and tomatoes",
        "price": "15.99",
        "ingredients": ["tomato sauce", "mozzarella", "bell peppers", "onions", "mushrooms", "olives", "tomatoes"],
        "allergens": ["dairy", "gluten"],
        "restaurant_category": "Pizza",
        "is_vegetarian": True,
        "is_vegan": False,
        "is_gluten_free": False,
        "is_dairy_free": False,
        "is_nut_free": True
    },
    {
        "title": "Gluten-Free Margherita Pizza",
        "description": "Classic Margherita pizza made with gluten-free crust",
        "price": "16.99",
        "ingredients": ["gluten-free crust", "tomato sauce", "mozzarella", "fresh basil", "olive oil"],
        "allergens": ["dairy"],
        "restaurant_category": "Pizza",
        "is_vegetarian": True,
        "is_vegan": False,
        "is_gluten_free": True,
        "is_dairy_free": False,
        "is_nut_free": True
    }
]

def test_pizza_search():
    """Test current pizza search functionality"""
    print("🧪 TESTING CURRENT PIZZA SEARCH")
    print("=" * 50)
    
    url = 'https://restaurantchat-production.up.railway.app/chat'
    data = {
        'message': 'Show me pizza options',
        'client_id': str(uuid.uuid4()),
        'restaurant_id': 'bella_vista_restaurant'
    }
    
    try:
        response = requests.post(url, json=data, timeout=35)
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            if 'pizza' in answer.lower() and 'not have' in answer.lower():
                print("❌ CURRENT STATUS: Pizza not found")
                print(f"Response: {answer[:200]}...")
                return False
            else:
                print("✅ CURRENT STATUS: Pizza found")
                print(f"Response: {answer[:200]}...")
                return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def test_margherita_search():
    """Test current Margherita search functionality"""
    print("\n🧪 TESTING CURRENT MARGHERITA SEARCH")
    print("=" * 50)
    
    url = 'https://restaurantchat-production.up.railway.app/chat'
    data = {
        'message': 'Show me Margherita',
        'client_id': str(uuid.uuid4()),
        'restaurant_id': 'bella_vista_restaurant'
    }
    
    try:
        response = requests.post(url, json=data, timeout=35)
        if response.status_code == 200:
            result = response.json()
            answer = result.get('answer', '')
            
            if 'margherita' in answer.lower() and 'not have' in answer.lower():
                print("❌ CURRENT STATUS: Margherita not found")
                print(f"Response: {answer[:200]}...")
                return False
            else:
                print("✅ CURRENT STATUS: Margherita found")
                print(f"Response: {answer[:200]}...")
                return True
        else:
            print(f"❌ HTTP Error: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Exception: {e}")
        return False

def create_pizza_menu_update():
    """Create the pizza menu update data structure"""
    print("\n📝 CREATING PIZZA MENU UPDATE")
    print("=" * 50)
    
    # Create the update structure
    update_data = {
        "data": {
            "menu": PIZZA_ITEMS
        }
    }
    
    print("Pizza items to add:")
    for i, item in enumerate(PIZZA_ITEMS, 1):
        print(f"  {i}. {item['title']} - ${item['price']}")
        print(f"     Category: {item['restaurant_category']}")
        print(f"     Vegetarian: {item['is_vegetarian']}")
        print(f"     Gluten-Free: {item['is_gluten_free']}")
        print()
    
    return update_data

def main():
    """Main function to test and prepare pizza menu update"""
    print("🍕 PIZZA MENU UPDATE SCRIPT")
    print("=" * 60)
    
    # Test current functionality
    pizza_works = test_pizza_search()
    margherita_works = test_margherita_search()
    
    # Create update data
    update_data = create_pizza_menu_update()
    
    print("\n📊 SUMMARY")
    print("=" * 50)
    print(f"Current pizza search: {'✅ Works' if pizza_works else '❌ Fails'}")
    print(f"Current Margherita search: {'✅ Works' if margherita_works else '❌ Fails'}")
    print(f"Pizza items to add: {len(PIZZA_ITEMS)}")
    
    print("\n🔧 NEXT STEPS")
    print("=" * 50)
    print("1. Use the restaurant update endpoint to add pizza items")
    print("2. Test pizza search functionality after update")
    print("3. Verify fallback logic works for pizza")
    
    # Save update data to file
    with open('temporary/pizza_menu_update.json', 'w') as f:
        json.dump(update_data, f, indent=2)
    
    print(f"\n💾 Update data saved to: temporary/pizza_menu_update.json")

if __name__ == "__main__":
    main()

