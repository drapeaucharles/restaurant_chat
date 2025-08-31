# Tool Calling Implementation Guide

## Overview
We've successfully implemented tool calling functionality that allows MIA to query the database for specific dish details instead of hallucinating information. This implementation extends the existing `full_menu` service without breaking it.

## Key Components

### 1. New Service: `mia_chat_service_full_menu_with_tools.py`
- Extends the existing full_menu service
- Adds tool execution capabilities
- Falls back to full_menu behavior on any error
- Supports multi-round communication with MIA

### 2. Available Tools
- **get_dish_details**: Get complete details about a specific dish
- **search_menu_items**: Search by ingredient, category, or name  
- **filter_by_dietary**: Find dishes by dietary restrictions

### 3. Integration in `chat_dynamic.py`
- Added feature flag: `ENABLE_FULL_MENU_TOOLS`
- Automatically upgrades to tool-enabled service for relevant queries
- Pattern matching for tool-triggering phrases

## Activation

### Enable Tool Calling
Add to your `.env` file:
```bash
ENABLE_FULL_MENU_TOOLS=true
```

### Without Feature Flag
Restaurants can directly use the tool-enabled service by setting:
```sql
UPDATE restaurants SET rag_mode = 'full_menu_with_tools' WHERE restaurant_id = 'your_restaurant_id';
```

## How It Works

1. **Query Analysis**: System checks if query contains patterns like "tell me about", "ingredients", "allergens", etc.

2. **Tool Selection**: If patterns match and feature flag is enabled, upgrades to tool-enabled service

3. **MIA Communication**: 
   - Sends available tools to MIA along with the prompt
   - MIA can request tool execution
   - Service executes tool and sends results back
   - MIA generates final response with accurate data

4. **Fallback**: Any error automatically falls back to standard full_menu service

## Testing

Use the provided test script:
```bash
python3 test_tools_service.py
```

## Benefits

1. **Accuracy**: No more hallucinated dish details
2. **Backward Compatible**: Won't break existing functionality
3. **Gradual Rollout**: Feature flag allows testing
4. **Extensible**: Easy to add new tools

## Next Steps

1. Monitor tool usage in production
2. Add more tools as needed (e.g., reservation queries)
3. Optimize tool execution performance
4. Add analytics to track tool usage patterns