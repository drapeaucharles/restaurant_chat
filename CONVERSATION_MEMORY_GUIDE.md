# Enhanced Conversation Memory for RAG System

## Overview

The enhanced conversation memory system enables the RAG chatbot to maintain context across multiple interactions, providing more natural and personalized conversations. It stores the last 5-10 messages and intelligently extracts preferences, topics, and context.

## Key Features

### 1. Full Conversation History
- Stores complete query-response pairs (not just truncated)
- Maintains metadata including query type, confidence, and mentioned items
- 4-hour retention window (configurable)
- Automatic fallback to in-memory storage if Redis unavailable

### 2. Intelligent Context Extraction
- **Dietary Preferences**: Automatically detects vegetarian, vegan, gluten-free mentions
- **Allergen Tracking**: Remembers mentioned allergies for safer recommendations
- **Category Interests**: Tracks which food categories customer asks about
- **Price Sensitivity**: Identifies budget-conscious vs quality-focused customers
- **Spice Preferences**: Notes mild vs spicy preferences

### 3. Ambiguous Query Detection
Identifies when clarification is needed:
- "How much does it cost?" (what item?)
- "Is it spicy?" (which dish?)
- "I'll take that" (take what?)
- Considers time gaps (>5 minutes) as stale context

### 4. Context-Aware Responses
The system provides context to the AI in multiple ways:
- Recent conversation history (last 5 exchanges)
- Extracted preferences summary
- Last mentioned menu items
- Topic patterns from conversation

## Implementation

### Enable Enhanced Conversation Memory

Set the environment variable:
```bash
export RAG_MODE=enhanced_v3
```

### How It Works

1. **Storage**: Each conversation turn is stored with:
   ```python
   {
       "query": "Customer question",
       "response": "AI response",
       "timestamp": "ISO timestamp",
       "metadata": {
           "query_type": "recommendation",
           "confidence": 0.85,
           "mentioned_items": ["Pasta Primavera"],
           "allergens": ["nuts"]
       }
   }
   ```

2. **Context Building**: For each query, the system:
   - Retrieves conversation history
   - Extracts preferences and patterns
   - Formats context for the AI prompt
   - Detects if clarification needed

3. **AI Prompt Enhancement**: Context is added as:
   ```
   === CONTEXT START ===
   --- 💬 PREVIOUS CONVERSATION ---
   Customer: Do you have vegetarian options?
   Assistant: Yes! We have Garden Salad, Margherita Pizza...
   
   --- ⭐ CUSTOMER PREFERENCES ---
   Dietary restrictions: vegetarian, nuts
   Interested in: pasta, salads
   === CONTEXT END ===
   ```

## Example Conversations

### Before (No Memory):
```
Customer: "What vegetarian dishes do you have?"
AI: "We have several vegetarian options including..."

Customer: "Which ones are nut-free?"
AI: "Our nut-free dishes include..." [No context of vegetarian requirement]
```

### After (With Memory):
```
Customer: "What vegetarian dishes do you have?"
AI: "We have several vegetarian options including..."

Customer: "Which ones are nut-free?"
AI: "From our vegetarian options, the nut-free choices are..." [Remembers both requirements]
```

## Configuration Options

### Memory Settings
```python
# In conversation_memory_enhanced.py
self.max_memory_items = 10  # Number of turns to keep
self.memory_duration = timedelta(hours=4)  # How long to remember
self.context_window = 5  # Turns to include in prompt
```

### Redis Configuration
```python
# Redis connection (falls back to in-memory if unavailable)
self.redis_client = redis.Redis(
    host='localhost',
    port=6379,
    decode_responses=True,
    socket_connect_timeout=2
)
```

## Testing

Run the test script to verify functionality:
```bash
python3 test_conversation_memory_simple.py
```

This tests:
- Conversation storage and recall
- Preference extraction
- Context formatting
- Ambiguous query detection
- In-memory fallback

## Benefits

1. **Better Follow-ups**: Natural handling of "What about..." questions
2. **Personalization**: Remembers dietary restrictions and preferences
3. **Reduced Repetition**: Customer doesn't need to re-state requirements
4. **Smarter Clarifications**: Asks for clarification only when needed
5. **Safety**: Tracks allergen mentions for safer recommendations

## Future Enhancements

1. **Cross-Session Memory**: Remember returning customers
2. **Learning from Feedback**: Adjust based on order history
3. **Group Patterns**: Learn from similar customer profiles
4. **Proactive Suggestions**: "Based on your preferences..."
5. **Multi-Restaurant Context**: Preferences that carry across restaurants