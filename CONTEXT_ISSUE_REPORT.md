# Restaurant Context and Menu Passing Issue Report

## Executive Summary
The restaurant menu and context are not being properly passed to the MIA AI service due to a data structure mismatch. The menu exists in the database but is not being accessed correctly by the chat service.

## Issue Details

### 1. Data Structure Mismatch
**Problem**: The MIA chat service expects menu data at `restaurant.data.menu`, but the actual structure has menu at the top level.

**Current Code** (mia_chat_service.py line 311-315):
```python
data = restaurant.data or {}
# ...
menu_items = data.get("menu", [])
```

**Actual Data Structure**:
- Restaurant endpoint returns menu at top level: `response.menu`
- Restaurant model stores everything in `data` field as JSON
- There's a mismatch between API response and database structure

### 2. Menu Data Availability
**Good News**: The menu data exists and is comprehensive
- Bella Vista restaurant has 50+ menu items
- Each item has complete information (name, ingredients, allergens, price, etc.)

**Bad News**: The chat service can't access it due to the structure issue

### 3. Context Filtering
The `format_menu_for_context` function only includes menu items that are "relevant" to the query:
- Only includes items if their name or ingredients appear in the user's question
- For general queries, it only shows first 10 item names
- This means most menu items are never sent to the AI

## Impact

1. **AI Responses**: The AI is giving generic responses because it has no menu context
2. **User Experience**: Users get unhelpful answers like "I'd be happy to help with our menu" instead of actual menu information
3. **Lost Functionality**: The AI can't recommend dishes, describe ingredients, or provide allergen information

## Root Cause Analysis

The issue appears to stem from an API/database design inconsistency:

1. **Database**: Stores all restaurant data (menu, hours, etc.) in a single JSON `data` field
2. **API Response**: Flattens this structure, putting menu at the top level
3. **Chat Service**: Expects the database structure, not the API structure

## Recommended Solutions

### Option 1: Quick Fix (Minimal Changes)
Update the restaurant info endpoint to match what the chat service expects:

```python
# In restaurant route, wrap response in 'data' field
return {
    "restaurant_id": restaurant.restaurant_id,
    "name": restaurant_name,
    "data": {
        "menu": menu_items,
        "opening_hours": opening_hours,
        # ... other fields
    }
}
```

### Option 2: Fix Chat Service (Recommended)
Update mia_chat_service.py to handle both structures:

```python
# Line 311-315 in mia_chat_service.py
# Handle both database structure and API response structure
if hasattr(restaurant, 'data') and restaurant.data:
    data = restaurant.data
    menu_items = data.get("menu", [])
else:
    # Direct attributes from API response
    menu_items = getattr(restaurant, 'menu', [])
    data = {
        'opening_hours': getattr(restaurant, 'opening_hours', {}),
        'contact_info': getattr(restaurant, 'contact_info', {})
    }
```

### Option 3: Improve Context Building
Send more complete menu context for general queries:

```python
def format_menu_for_context(menu_items, query):
    # For general queries, include all categories and sample items
    if any(word in query.lower() for word in ['menu', 'serve', 'have', 'offer']):
        categories = {}
        for item in menu_items:
            cat = item.get('subcategory', 'main')
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(item.get('name'))
        
        context = "Menu Categories:\n"
        for cat, items in categories.items():
            context += f"- {cat}: {', '.join(items[:5])}...\n"
        return context
    
    # Continue with existing relevant item filtering...
```

## Testing Results

When properly formatted context was provided to MIA:
- Vegetarian query → AI correctly recommended Margherita Pizza and Caprese Salad
- Pasta query → AI described Spaghetti Carbonara and Penne Arrabbiata
- The AI model works well when given proper context

## Next Steps

1. **Immediate**: Implement Option 2 fix to handle both data structures
2. **Short-term**: Improve context building to include more menu information
3. **Long-term**: Standardize data structure between database and API

## Conclusion

The MIA integration is working correctly from a technical standpoint. The issue is purely about data access - the menu exists but isn't being passed to the AI. Once this structural issue is fixed, the restaurant chat should provide detailed, context-aware responses about the menu.