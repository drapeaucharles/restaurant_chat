# Command-R Architecture for MIA

## Overview
Transitioning from Qwen2.5-7B to Command-R-7B-AWQ with native function calling support for efficient data queries.

## Architecture Components

### 1. MIA Backend (Miner)
- **Model**: Command-R-7B-AWQ (quantized for efficiency)
- **Features**:
  - Native function/tool calling
  - Multilingual support (EN/FR/RU/ID)
  - Customer support optimized
  - 40-60 tokens/sec performance

### 2. Restaurant Backend
- **Service**: `mia_chat_service_full_menu_compact`
- **Approach**: Sends compact menu catalog + tool definitions
- **Tools Available**:
  - `get_dish_details` - Full dish information
  - `search_by_ingredient` - Find dishes with ingredients
  - `filter_by_category` - Get dishes by category
  - `check_dietary_restriction` - Find suitable dishes

### 3. Flow

```
1. User: "What's in the Lobster Ravioli?"
   ↓
2. Restaurant Backend → MIA:
   - Compact menu (name, price, category)
   - Tool definitions
   - Conversation history
   ↓
3. MIA Response:
   <tool_call>
   {"name": "get_dish_details", "parameters": {"dish_name": "Lobster Ravioli"}}
   </tool_call>
   ↓
4. Restaurant Backend executes tool:
   Returns: {description, ingredients, allergens, price}
   ↓
5. Restaurant Backend → MIA:
   Tool result data
   ↓
6. MIA generates natural response:
   "Our Lobster Ravioli features fresh Maine lobster..."
```

## Implementation Steps

### Step 1: Install Command-R on MIA Backend
```bash
cd /home/charles-drapeau/Documents/Project/MIA_project/mia-backend
bash install-command-r-7b-awq.sh
```

### Step 2: Update Businesses to Compact Mode
```python
UPDATE businesses SET rag_mode = 'full_menu_compact';
```

### Step 3: Test Integration
```bash
cd Restaurant/BackEnd
python test_full_menu_compact.py
```

## Benefits
- **Smaller prompts**: Only essential menu data sent
- **Dynamic details**: AI fetches what it needs
- **Better accuracy**: Focused context
- **Universal**: Works for any business type
- **Multilingual**: Excellent language support

## Migration Path
1. Keep existing Qwen miner running
2. Deploy Command-R miner on new GPU
3. Test with select businesses
4. Gradually migrate all businesses
5. Deprecate Qwen miner

## Performance Expectations
- Initial response: 8-10 seconds
- With tool call: 10-14 seconds (2 round trips)
- Token generation: 40-60 tokens/sec
- Memory usage: ~8GB VRAM with AWQ

## Fallback Strategy
If Command-R-7B-AWQ not available:
1. Try full Command-R model
2. Fall back to Qwen2.5-7B
3. Tool calling still works via prompt engineering