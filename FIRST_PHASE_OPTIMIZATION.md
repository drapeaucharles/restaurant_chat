# First Phase Optimization Suggestions

## Current Approach
We send ALL tools in first iteration, which has drawbacks:
- Large token usage
- AI might get confused with too many options
- Not scalable when we add more tools

## Suggestions for Better First Phase

### 1. **Tool Categories Instead of Full Tools**
Instead of sending full tool definitions, send categories:

```python
TOOL_CATEGORIES = {
    "menu_query": ["get_dish_details", "search_menu_items"],
    "dietary": ["filter_by_dietary", "check_allergens"],
    "reservation": ["check_availability", "make_booking"],
    "general": ["get_restaurant_info", "get_hours"]
}

# First phase: Send only categories
prompt = """
Customer: "I have a nut allergy and want pasta"

Identify which tool categories are needed:
- menu_query: For finding specific dishes
- dietary: For allergies/restrictions
- reservation: For booking tables
- general: For restaurant info

Return: ["menu_query", "dietary"]
"""
```

### 2. **Intent Detection Without Tools**
First phase could be pure intent detection:

```python
# Phase 1: Lightweight intent detection
prompt = """
Analyze: "I have a nut allergy and want pasta"

Return JSON:
{
    "intents": ["dietary_restriction", "menu_search"],
    "entities": {
        "allergy": "nuts",
        "dish_type": "pasta"
    }
}
"""

# Backend maps intents to tools
intent_to_tools = {
    "dietary_restriction": "filter_by_dietary",
    "menu_search": "search_menu_items"
}
```

### 3. **Function Calling with Minimal Schema**
Send simplified tool schemas:

```python
MINIMAL_TOOLS = [
    {
        "name": "search_menu",
        "when": "customer asks about dishes/categories",
        "needs": "search_term"
    },
    {
        "name": "dietary_filter",
        "when": "customer has allergies/restrictions",
        "needs": "restriction_type"
    }
]
```

### 4. **Business-Specific Tool Sets**
Different tool sets per business type:

```python
def get_tools_for_business(business_type: str):
    if business_type == "restaurant":
        return RESTAURANT_TOOLS
    elif business_type == "legal":
        return LEGAL_TOOLS
    elif business_type == "medical":
        return MEDICAL_TOOLS
    
# First phase gets only relevant tools
```

### 5. **Progressive Tool Discovery**
Start simple, add complexity if needed:

```python
# Phase 1a: Basic intent
response = analyze_basic_intent(message)

if response.needs_tools:
    # Phase 1b: Get specific tools
    tools = get_relevant_tools(response.intents)
    response = analyze_with_tools(message, tools)
```

## Recommended Approach

### Option A: Intent-First (Most Efficient)
```python
# Phase 1: Intent only (no tools)
intents = detect_intents(message)  # Returns: ["allergy", "menu_search"]

# Backend decides tools
tools_to_use = map_intents_to_tools(intents)

# Phase 2: Execute tools
results = execute_tools(tools_to_use)

# Phase 3: Generate response
response = generate_response(results)
```

### Option B: Lightweight Tool Matching
```python
# Phase 1: Send tool patterns, not full schemas
TOOL_PATTERNS = [
    {"pattern": "allergy|allergic|can't eat", "tool": "filter_by_dietary"},
    {"pattern": "what.*have|menu|dishes", "tool": "search_menu_items"},
    {"pattern": "tell me about|details|ingredients", "tool": "get_dish_details"}
]

# AI matches patterns and returns tool names only
```

### Option C: Dynamic Tool Loading
```python
# Phase 1: Categorize query
category = categorize_query(message)  # Returns: "menu_with_dietary"

# Load specific tools for category
tools = load_tools_for_category(category)

# Phase 2: Use those specific tools
```

## Benefits of These Approaches

1. **Reduced Tokens**: Don't send full tool schemas unnecessarily
2. **Better Accuracy**: AI focuses on intent, not tool selection
3. **Scalable**: Easy to add new tools without affecting intent detection
4. **Business Agnostic**: Intent detection works across all business types
5. **Faster**: Smaller prompts = faster responses

## Implementation Priority

1. Start with **Intent-First** approach (Option A)
2. Test and measure performance
3. Add complexity only if needed
4. Keep tool execution in backend (Phase 2)
5. Use full context only for final response (Phase 3)