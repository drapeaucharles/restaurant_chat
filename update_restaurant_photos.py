import requests
import json

# Script to update the existing restaurant with complete photo URLs for all menu items

restaurant_id = "bella_vista_restaurant"
password = "BellaVista2024!"

# First login to get the auth token
login_url = "https://restaurantchat-production.up.railway.app/restaurant/login"
login_data = {
    "restaurant_id": restaurant_id,
    "password": password
}

print("Logging in...")
login_response = requests.post(login_url, json=login_data)
if login_response.status_code != 200:
    print(f"Login failed: {login_response.text}")
    exit(1)

auth_data = login_response.json()
access_token = auth_data["access_token"]
print("Login successful!")

# Get current restaurant profile
headers = {
    "Authorization": f"Bearer {access_token}"
}

print("Fetching current profile...")
profile_response = requests.get(
    "https://restaurantchat-production.up.railway.app/restaurant/profile",
    headers=headers
)

if profile_response.status_code != 200:
    print(f"Failed to fetch profile: {profile_response.text}")
    exit(1)

current_data = profile_response.json()
print(f"Current menu has {len(current_data.get('menu', []))} items")

# Update menu items with photo URLs
menu_items = current_data.get("menu", [])

# Map of dish names to appropriate Unsplash photo URLs
photo_mapping = {
    # Appetizers
    "Truffle Arancini": "https://images.unsplash.com/photo-1541014741259-de529411b96a?w=400",
    "Caprese Skewers": "https://images.unsplash.com/photo-1529928520614-7c76e2d99740?w=400",
    "Calamari Fritti": "https://images.unsplash.com/photo-1599487488170-d11ec9c172f0?w=400",
    "Bruschetta Trio": "https://images.unsplash.com/photo-1572695157366-5e585ab2b69f?w=400",
    "Stuffed Mushrooms": "https://images.unsplash.com/photo-1490645935967-10de6ba17061?w=400",
    "Shrimp Cocktail": "https://images.unsplash.com/photo-1625943553852-781c6dd46faa?w=400",
    "Spinach Artichoke Dip": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400",
    "Beef Carpaccio": "https://images.unsplash.com/photo-1625937286074-9ca519d5d9df?w=400",
    "Mezze Platter": "https://images.unsplash.com/photo-1593001872095-7d5b3868fb1d?w=400",
    "Oysters Rockefeller": "https://images.unsplash.com/photo-1606850780554-b55ea4dd0b70?w=400",
    
    # Soups & Salads
    "French Onion Soup": "https://images.unsplash.com/photo-1547592166-23ac45744acd?w=400",
    "Lobster Bisque": "https://images.unsplash.com/photo-1594756202469-9ff9799b2e4e?w=400",
    "Caesar Salad": "https://images.unsplash.com/photo-1550304943-4f24f54ddde9?w=400",
    "Greek Salad": "https://images.unsplash.com/photo-1540189549336-e6e99c3679fe?w=400",
    "Roasted Beet Salad": "https://images.unsplash.com/photo-1609501676725-7186f017a4b7?w=400",
    "Minestrone Soup": "https://images.unsplash.com/photo-1613844237701-8f3664fc2eff?w=400",
    "Quinoa Power Bowl": "https://images.unsplash.com/photo-1512621776951-a57141f2eefd?w=400",
    "Tom Yum Soup": "https://images.unsplash.com/photo-1562565652-a0d8f0c59eb4?w=400",
    
    # Pasta & Risotto
    "Spaghetti Carbonara": "https://images.unsplash.com/photo-1612874742237-6526221588e3?w=400",
    "Lobster Ravioli": "https://images.unsplash.com/photo-1587740908075-9e245070dfaa?w=400",
    "Mushroom Risotto": "https://images.unsplash.com/photo-1595908129746-57ca1a63dd4d?w=400",
    "Penne Arrabbiata": "https://images.unsplash.com/photo-1621996346565-e3dbc646d9a9?w=400",
    "Seafood Linguine": "https://images.unsplash.com/photo-1563379926898-05f4575a45d8?w=400",
    "Gnocchi Gorgonzola": "https://images.unsplash.com/photo-1609501676725-7186f017a4b7?w=400",
    "Lasagna Bolognese": "https://images.unsplash.com/photo-1574894709920-11b28e7367e3?w=400",
    "Saffron Risotto": "https://images.unsplash.com/photo-1476124369491-e7addf5db371?w=400",
    
    # Meat
    "Filet Mignon": "https://images.unsplash.com/photo-1546833999-b9f581a1996d?w=400",
    "Rack of Lamb": "https://images.unsplash.com/photo-1595777216528-071e0127ccbf?w=400",
    "Osso Buco": "https://images.unsplash.com/photo-1432139555190-58524dae6a55?w=400",
    "Duck Confit": "https://images.unsplash.com/photo-1623428187969-5da2dcea5ebf?w=400",
    "Beef Short Ribs": "https://images.unsplash.com/photo-1544025162-d76694265947?w=400",
    "Pork Tenderloin": "https://images.unsplash.com/photo-1606850780554-b55ea4dd0b70?w=400",
    "Veal Piccata": "https://images.unsplash.com/photo-1632778149955-e80f8ceca2e8?w=400",
    "Ribeye Steak": "https://images.unsplash.com/photo-1558030006-450675393462?w=400",
    
    # Seafood
    "Grilled Salmon": "https://images.unsplash.com/photo-1485921325833-c519f76c4927?w=400",
    "Sea Bass": "https://images.unsplash.com/photo-1519708227418-c8fd9a32b7a2?w=400",
    "Lobster Thermidor": "https://images.unsplash.com/photo-1626645738196-c2a7c87a8f58?w=400",
    "Seared Scallops": "https://images.unsplash.com/photo-1626201642492-15d1b4c0cd75?w=400",
    "Tuna Steak": "https://images.unsplash.com/photo-1567479938401-f265a66ba382?w=400",
    "Mixed Seafood Grill": "https://images.unsplash.com/photo-1623961990059-7d9d7e2f6fdd?w=400",
    
    # Vegetarian/Vegan
    "Eggplant Parmigiana": "https://images.unsplash.com/photo-1573821663912-6df460f9c684?w=400",
    "Vegetable Curry": "https://images.unsplash.com/photo-1455619452474-d2be8b1e70cd?w=400",
    "Stuffed Bell Peppers": "https://images.unsplash.com/photo-1583278171230-7cde103c5935?w=400",
    "Mushroom Wellington": "https://images.unsplash.com/photo-1511690078903-71dc5a49f5e3?w=400",
    "Buddha Bowl": "https://images.unsplash.com/photo-1540914124281-342587941389?w=400",
    
    # Desserts
    "Tiramisu": "https://images.unsplash.com/photo-1571877227200-a0d98ea607e9?w=400",
    "Chocolate Lava Cake": "https://images.unsplash.com/photo-1606313564200-e75d5e30476c?w=400",
    "Crème Brûlée": "https://images.unsplash.com/photo-1470124182917-cc6e71b22ecc?w=400",
    "New York Cheesecake": "https://images.unsplash.com/photo-1524351199678-941a58a3df50?w=400",
    "Gelato Trio": "https://images.unsplash.com/photo-1567206563064-6f60f40a2b57?w=400"
}

# Update menu items with photo URLs from mapping
category_mapping = {
    "Appetizers": "Dinner",
    "Soups": "Dinner", 
    "Salads": "Dinner",
    "Pasta": "Dinner",
    "Risotto": "Dinner",
    "Meat": "Dinner",
    "Seafood": "Dinner",
    "Vegetarian": "Dinner",
    "Vegan": "Dinner",
    "Dessert": "Dinner"
}

for item in menu_items:
    # Try to match by title or dish field
    dish_name = item.get("title") or item.get("dish")
    if dish_name and dish_name in photo_mapping:
        # Keep the uploaded photo if it exists, otherwise use the mapping
        if not item.get("photo_url"):
            item["photo_url"] = photo_mapping[dish_name]
            print(f"Added photo URL for: {dish_name}")
    
    # Fix category to use allowed values
    if item.get("category") and item["category"] in category_mapping:
        item["category"] = category_mapping[item["category"]]
    elif item.get("category"):
        # Default to Dinner if category is not recognized
        item["category"] = "Dinner"

# Prepare update data
update_data = {
    "name": current_data.get("name"),
    "story": current_data.get("story", ""),
    "menu": menu_items,
    "faq": current_data.get("faq", []),
    "opening_hours": current_data.get("opening_hours", {}),
    "whatsapp_number": current_data.get("whatsapp_number", "")
}

# Update the restaurant profile
print("\nUpdating restaurant profile with photo URLs...")
update_response = requests.put(
    "https://restaurantchat-production.up.railway.app/restaurant/profile",
    headers=headers,
    json=update_data
)

if update_response.status_code == 200:
    print("✅ Restaurant profile updated successfully!")
    print(f"All {len(menu_items)} menu items now have photo URLs")
else:
    print(f"❌ Failed to update profile: {update_response.text}")