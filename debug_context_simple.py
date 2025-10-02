#!/usr/bin/env python3
# Debug the context analysis functions - simple version

def extract_detailed_topic_from_message(message: str) -> str:
    """Extract detailed topic from a message, including specific food types"""
    message_lower = message.lower()
    
    # Check for specific food types first
    if any(word in message_lower for word in ["fish", "salmon", "tuna", "sea bass", "cod", "halibut"]):
        return "fish"
    elif any(word in message_lower for word in ["shrimp", "crab", "lobster", "oysters", "mussels", "scallops"]):
        return "shellfish"
    elif any(word in message_lower for word in ["pasta", "spaghetti", "penne", "linguine", "ravioli"]):
        return "pasta"
    elif any(word in message_lower for word in ["pizza", "margherita", "pepperoni"]):
        return "pizza"
    elif any(word in message_lower for word in ["chicken", "poultry"]):
        return "chicken"
    elif any(word in message_lower for word in ["beef", "steak", "burger"]):
        return "beef"
    elif any(word in message_lower for word in ["seafood", "sea", "ocean"]):
        return "seafood"
    elif any(word in message_lower for word in ["dessert", "sweet", "cake", "ice cream"]):
        return "dessert"
    elif any(word in message_lower for word in ["salad", "greens"]):
        return "salad"
    else:
        return "general"

def is_follow_up_question(message: str, chat_history) -> bool:
    """Check if message is a follow-up question that should maintain context"""
    message_lower = message.lower()
    
    # Follow-up indicators
    follow_up_phrases = [
        "any other", "what else", "more", "another", "different", 
        "anything else", "other options", "other choices", "also have",
        "besides", "in addition", "as well", "too"
    ]
    
    return any(phrase in message_lower for phrase in follow_up_phrases)

def get_context_from_previous_message(chat_history) -> str:
    """Get the topic context from the previous user message"""
    if not chat_history:
        return "general"
    
    # Look at the last user message
    for msg in reversed(chat_history):
        if msg.get("role") == "user":
            return extract_detailed_topic_from_message(msg.get("message", ""))
    
    return "general"

# Test the context analysis functions
print('🔍 DEBUGGING CONTEXT ANALYSIS FUNCTIONS')
print('='*50)

# Simulate the chat history from the user's log
chat_history = [
    {'role': 'user', 'message': 'Hello ! How are you today'},
    {'role': 'assistant', 'message': 'Hey there! I am doing great, thanks for asking...'},
    {'role': 'user', 'message': 'Yes i want to eat something from the sea !'},
    {'role': 'assistant', 'message': 'Sure thing! How about the Calamari Fritti...'},
    {'role': 'user', 'message': 'any fish?'},
    {'role': 'assistant', 'message': 'Got it! How about the Sea Bass for $32.99...'}
]

current_message = 'any other?'

print(f'Current message: "{current_message}"')
print(f'Chat history length: {len(chat_history)}')

# Test follow-up detection
is_follow_up = is_follow_up_question(current_message, chat_history)
print(f'Is follow-up: {is_follow_up}')

# Test previous topic extraction
previous_topic = get_context_from_previous_message(chat_history)
print(f'Previous topic: {previous_topic}')

# Test detailed topic extraction for the last user message
last_user_message = 'any fish?'
detailed_topic = extract_detailed_topic_from_message(last_user_message)
print(f'Detailed topic for "{last_user_message}": {detailed_topic}')

# Test what the context should be
print('\n🎯 EXPECTED RESULTS:')
print('- Is follow-up: True ("any other?" contains "any other")')
print('- Previous topic: "fish" (from "any fish?")')
print('- Should maintain context: True')

print('\n🔍 CHAT HISTORY ANALYSIS:')
for i, msg in enumerate(chat_history):
    print(f'  {i}: {msg["role"]} - "{msg["message"][:50]}..."')

# Test the logic
maintain_context = is_follow_up and previous_topic != "general"
print(f'\nMaintain context: {maintain_context}')
print(f'Should use search_by_food_type with "Fish": {maintain_context and previous_topic == "fish"}')
