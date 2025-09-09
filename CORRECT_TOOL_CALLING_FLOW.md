# Correct Tool Calling Flow - Single Response Architecture

## The Better Design
Backend should handle the entire tool flow internally and only return once to the client with the final answer.

## Correct Flow

### 1. Client Sends Message
```
Customer -> Restaurant Backend: "Tell me about the Carbonara"
```

### 2. Backend First AI Call (Tool Discovery)
```python
# Minimal context - just enough to identify if tools needed
{
    "message": "Customer asks: Tell me about the Carbonara",
    "tools": [...available tools...],
    "context": {
        "restaurant_name": "Bella Vista",
        # NO full menu - keep it light
    }
}
```

### 3. AI Responds (Internal Only)
```json
{
    "response": "Let me check that for you",  // This is NOT sent to customer
    "tool_calls": [{
        "function": {
            "name": "get_dish_details",
            "arguments": "{\"dish_name\": \"Carbonara\"}"
        }
    }]
}
```

### 4. Backend Executes Tool
```python
# Execute locally
dish_data = execute_tool("get_dish_details", {"dish_name": "Carbonara"})
```

### 5. Backend Second AI Call (Full Context)
```python
# Now with full context and tool results
{
    "message": f"""
You are Maria from Bella Vista restaurant.

Customer asked: Tell me about the Carbonara

Tool result:
{dish_data}

Provide a natural, friendly response using this information.
""",
    "context": {
        "restaurant_name": "Bella Vista",
        "system_prompt": full_maria_prompt,
        # Include any customer preferences/history
    },
    "tools": []  # No tools on second call
}
```

### 6. AI Final Response
```
"Our Spaghetti Carbonara is a classic Roman dish made with guanciale, 
pecorino romano, eggs, and black pepper. It's priced at $18 and is 
one of our most popular pasta dishes. I should mention it contains 
gluten, dairy, and eggs. Would you like to know about wine pairings?"
```

### 7. Backend Returns to Client
```python
# Only NOW does customer see response
return {
    "answer": final_ai_response,
    "response_id": "...",
    "confidence_score": 0.95
}
```

## Key Architecture Points

### Single Response to Client
- Customer sends message
- Waits 2-3 seconds  
- Gets complete, accurate answer
- Never sees intermediate "Let me check" messages

### Two-Phase Internal Processing
1. **Discovery Phase**: Light context, identify tools needed
2. **Response Phase**: Full context, use tool results

### Benefits
- **Faster**: No round trips to client
- **Cleaner**: Customer sees only final response
- **Efficient**: Minimal context in first call saves tokens
- **Accurate**: Tool data used in final response

## Example Implementation

```python
async def process_message(customer_message: str, restaurant_id: str):
    # Phase 1: Tool Discovery (light context)
    tool_response = await mia_chat(
        message=customer_message,
        tools=AVAILABLE_TOOLS,
        context={"restaurant_name": restaurant.name},
        max_tokens=100  # Keep it short
    )
    
    final_response = None
    
    if tool_response.has_tool_calls:
        # Execute tools
        tool_results = []
        for tool_call in tool_response.tool_calls:
            result = execute_tool(tool_call.name, tool_call.arguments)
            tool_results.append(result)
        
        # Phase 2: Generate Response (full context)
        final_response = await mia_chat(
            message=build_full_prompt(customer_message, tool_results),
            context=full_restaurant_context,
            tools=[]  # No tools in second call
        )
    else:
        # No tools needed, use the first response
        final_response = tool_response
    
    # Return to customer
    return {
        "answer": final_response.text,
        "used_tools": tool_response.has_tool_calls
    }
```

## Workflow Diagram

```
Customer                Restaurant Backend              MIA AI
   |                            |                         |
   |---- "About Carbonara?" --->|                         |
   |                            |                         |
   |                            |---"Need tool?" -------->|
   |                            |                         |
   |                            |<-- get_dish_details ----|
   |                            |                         |
   |                            | [Execute tool locally]  |
   |                            |                         |
   |                            |-- Full context -------->|
   |                            |   + tool results        |
   |                            |                         |
   |                            |<-- Natural response ----|
   |                            |                         |
   |<--- "Our Carbonara..." ----|                         |
```

## Why This is Better

1. **Performance**: One round trip to client instead of multiple
2. **UX**: No intermediate "checking..." messages
3. **Token Efficiency**: First call uses minimal context
4. **Flexibility**: Backend controls entire flow
5. **Error Handling**: Can retry internally without customer knowing

This is the production-ready approach where the backend orchestrates the entire tool flow internally.