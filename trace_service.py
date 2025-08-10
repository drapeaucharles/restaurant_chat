"""
Trace which service is actually being used
"""

# Check config
from config import USE_MIA_FOR_CHAT, get_chat_service

print("Configuration:")
print(f"  USE_MIA_FOR_CHAT: {USE_MIA_FOR_CHAT}")

# Get the service from config
service = get_chat_service()
print(f"  get_chat_service returns: {service.__module__}.{service.__name__}")

# Check what chat_service actually is
from services.chat_service import chat_service
print(f"  chat_service is from: {chat_service.__module__}")

# Check if it's OpenAI or something else
import inspect
source = inspect.getsource(chat_service)
if "openai" in source:
    print("  chat_service uses OpenAI")
elif "mia" in source.lower():
    print("  chat_service references MIA")
else:
    print("  chat_service type unclear")

# The key question: Does chat_service internally use config?
if "get_chat_service" in source or "config" in source:
    print("  ⚠️  chat_service imports from config - might be recursive!")
else:
    print("  ✅ chat_service is standalone")