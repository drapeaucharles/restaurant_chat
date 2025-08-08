"""
Updated main.py with MIA integration support
This version checks config to use either regular chat or MIA chat
"""

# Add this section to your main.py after the imports:

# Import configuration
try:
    from config import USE_MIA_FOR_CHAT
except ImportError:
    USE_MIA_FOR_CHAT = False

# Conditional import based on configuration
if USE_MIA_FOR_CHAT:
    from routes import auth, restaurant, clients, chats, whatsapp, speech, smartlamp, update_subcategories, restaurant_categories
    from routes import chat_mia as chat  # Use MIA-integrated chat
    print("🤖 Using MIA for chat responses")
else:
    from routes import auth, restaurant, chat, clients, chats, whatsapp, speech, smartlamp, update_subcategories, restaurant_categories
    print("🤖 Using OpenAI for chat responses")

# Then in the router section, keep everything the same:
# app.include_router(chat.router)  # This will use the right chat module