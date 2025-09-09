# Intended Tool Calling Flow

## Vision
Enable the AI assistant (Maria) to provide accurate, real-time information about menu items by querying the actual database instead of relying on static context or hallucinating details.

## The Problem Being Solved
Previously, when customers asked specific questions like:
- "Does the Carbonara contain nuts?"
- "What's in the Truffle Arancini?"
- "Show me gluten-free options"

The AI would either:
1. Hallucinate ingredients based on general knowledge
2. Give generic responses
3. List the entire menu context

## The Desired Flow

### 1. Customer Query Arrives
```
Customer: "Tell me about the Truffle Arancini - what ingredients does it have?"
```

### 2. Restaurant Backend Processing
```python
# a) Detect query type
is_detail_query = contains("tell me about", "ingredients", "what's in")

# b) Prepare context with Maria persona + menu basics
system_prompt = "You are Maria from Bella Vista..."

# c) Include available tools
tools = [
    "get_dish_details",    # Get full info about specific dish
    "search_menu_items",   # Search by ingredient/category/name
    "filter_by_dietary"    # Filter by dietary restrictions
]
```

### 3. First MIA Call (With Tools)
```json
{
    "message": "Customer: Tell me about the Truffle Arancini...",
    "tools": [...],
    "tool_choice": "auto"
}
```

### 4. MIA Responds with Tool Request
```json
{
    "response": "Let me check that for you.",
    "tool_calls": [{
        "function": {
            "name": "get_dish_details",
            "arguments": "{\"dish_name\": \"Truffle Arancini\"}"
        }
    }]
}
```

### 5. Restaurant Backend Executes Tool
```python
# Execute locally without another API call
result = execute_tool("get_dish_details", {"dish_name": "Truffle Arancini"})

# Returns actual database data:
{
    "success": true,
    "dish": {
        "name": "Truffle Arancini",
        "price": "$12.99",
        "ingredients": ["arborio rice", "truffle oil", "parmesan"],
        "allergens": ["gluten", "dairy"],
        "description": "Golden-fried risotto balls..."
    }
}
```

### 6. Second MIA Call (With Tool Result)
```json
{
    "message": "Tool result: [dish details]\nNow provide a natural response",
    "tools": []  // No tools this time
}
```

### 7. MIA Provides Natural Response
```
"The Truffle Arancini is one of our most popular appetizers! It's made with 
creamy arborio rice infused with truffle oil and parmesan cheese, formed into 
balls and golden-fried until crispy. At $12.99, it contains gluten and dairy. 
The truffle oil gives it a wonderful earthy aroma that pairs beautifully with 
our house wines."
```

### 8. Customer Receives Accurate Information
- ✅ Correct ingredients from database
- ✅ Accurate allergen information
- ✅ Current price
- ✅ Natural, conversational tone
- ✅ Additional context (wine pairing)

## Key Benefits

### 1. Accuracy
- No hallucinated ingredients
- Real allergen data for safety
- Current prices

### 2. Efficiency  
- Only queries what's needed
- Doesn't dump entire menu
- Fast execution (tools run locally)

### 3. Natural Conversation
- AI decides when to use tools
- Maintains Maria's personality
- Provides helpful context

### 4. Safety
- Critical for allergen queries
- Never guesses about ingredients
- Can filter by dietary needs

## Tool Examples

### get_dish_details
**When**: Customer asks about specific dish
```
"What's in the Carbonara?"
"Tell me about the Truffle Arancini"
"Is the Caesar Salad vegetarian?"
```

### search_menu_items  
**When**: Customer looking for options
```
"What pasta dishes do you have?"
"Any seafood appetizers?"
"Show me dishes with truffle"
```

### filter_by_dietary
**When**: Dietary restrictions mentioned
```
"I'm vegan, what can I eat?"
"Show me gluten-free options"
"I have a nut allergy"
```

## The Complete Experience

```
Customer: "Hi, I have a nut allergy"
Maria: "I understand you have a nut allergy. Let me check our menu for safe options."
[Uses filter_by_dietary(["nut-free"])]
Maria: "I've found 15 dishes that are completely nut-free, including..."

Customer: "Tell me more about the Grilled Salmon"  
Maria: "Let me get the details for you."
[Uses get_dish_details("Grilled Salmon")]
Maria: "Our Grilled Salmon is a fantastic choice! It's fresh Atlantic salmon..."

Customer: "Perfect, I'll have that"
Maria: "Excellent choice! The Grilled Salmon is one of our most popular..."
```

## Why This Matters

1. **Trust**: Customers get accurate information
2. **Safety**: Allergen info is never guessed
3. **Personalization**: AI chooses when/what to query
4. **Efficiency**: Fast, targeted responses
5. **Scalability**: Works with any menu size

This system bridges the gap between static menu data and dynamic conversation, ensuring Maria can be both helpful and accurate.