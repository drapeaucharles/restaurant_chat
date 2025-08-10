"""
Check how menu items are categorized in the database
"""
import requests
import json

# First, let's get the restaurant data
print("Checking Bella Vista Restaurant menu data...")
print("="*60)

# We'll need to check the actual database data
# Let's create a debug endpoint to inspect the menu

# For now, let's analyze what we know:
print("\nKnown issues:")
print("1. Risotto is being returned when asking for pasta")
print("2. This suggests risotto has wrong category in DB")
print("\nPossible causes:")
print("- Menu items have a 'subcategory' field")
print("- Risotto might be marked as 'pasta' subcategory")
print("- Or the AI is matching 'risotto' when searching for pasta-like dishes")

print("\nNeed to check:")
print("1. Restaurant.data JSON structure")
print("2. How menu items are categorized")
print("3. The actual subcategory of Mushroom Risotto")

# Let's check the format_menu_for_context function
print("\nThe format_menu_for_context function in mia_chat_service.py:")
print("- Lines 99-162 show how menu context is built")
print("- It searches for items based on query words")
print("- Uses item name, description, and ingredients for matching")

print("\nRECOMMENDATION:")
print("Add a debug endpoint to inspect restaurant menu data")
print("This will show us the actual categorization")