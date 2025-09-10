# Claude Context - MIA Project

## Project Overview
This project consists of three interconnected systems:
1. **MIA Backend**: Orchestration service for GPU miners and job distribution
2. **GPU Miners**: Workers that process AI requests using vLLM
3. **Restaurant**: Restaurant chat system with AI-powered menu search and filtering

## Directory Structure
```
/home/charles-drapeau/Documents/Project/MIA_project/
├── mia-backend/          # MIA backend orchestrator
├── Restaurant/           # Restaurant chat system
│   ├── services/         # Backend AI services
│   ├── routes/           # API endpoints
│   ├── Front_end/        # React frontend
│   └── whatsapp-service/ # WhatsApp integration
└── temporary/            # Test scripts and results
```

## Critical Files and Their Purpose

### 1. GPU Miner Installer (IMPORTANT)
**Correct installer**: `/home/charles-drapeau/Documents/Project/MIA_project/Restaurant/install_miner_oneliner.sh`
- One-liner installation: `curl -sSL https://raw.githubusercontent.com/drapeaucharles/restaurant_chat/main/install_miner_oneliner.sh | bash`
- Registers miner with MIA backend
- Sets up bore tunneling for public access
- Creates systemd service for auto-restart
- **DO NOT USE**: Other installers in mia-backend/ are outdated

### 2. Main AI Service Implementation
**File**: `/home/charles-drapeau/Documents/Project/MIA_project/Restaurant/services/mia_chat_service_internal_tools_v5.py`

This is where ALL the AI logic lives:

#### Two-Phase System (Lines 723-1056)
```python
# PHASE 1: Tool Selection (Lines 723-759)
# - Sends context to MIA backend
# - Receives list of tools to execute with parameters
# Example: [{"tool": "search_by_food_type", "parameters": {"food_type": "Pasta"}}]

# PHASE 2: Response Generation (Lines 997-1052)
# - Executes selected tools locally
# - Sends results back to MIA for natural language response
```

#### Tool Execution (Lines 277-757)
- `execute_tool()`: Individual tool execution
- `execute_tools_single_pass()`: Optimized batch execution
- Tools include: search_by_food_type, filter_gluten_free, get_dish_details, etc.

#### Safety Guidelines (Lines 704-721)
- Critical section for allergen safety
- Prevents AI hallucination about allergens
- Trust pre-filtered data, never invent information

### 3. Database Configuration
- **Connection**: `postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway`
- **Test Restaurant**: `bella_vista_restaurant`
- **Menu Structure**: JSON with items containing allergens, ingredients, dietary flags

### 4. Testing Infrastructure
**Main test script**: `/home/charles-drapeau/Documents/Project/MIA_project/Restaurant/test_10_clients_sequential.py`
- Tests 10 clients with 2-10 questions each
- Sequential execution (wait between messages)
- Generates Q/A reports and debug logs
- Located in `test_results_YYYYMMDD_HHMMSS/`

## How the System Works

### Request Flow
1. **Customer** → Restaurant Frontend → Restaurant Backend
2. **Restaurant Backend** enriches request with menu context
3. **Phase 1**: Send to MIA Backend → GPU Miner → Get tool list
4. **Local Execution**: Restaurant Backend executes tools on menu data
5. **Phase 2**: Send results to MIA Backend → GPU Miner → Get response
6. **Response** → Customer

### MIA Backend Architecture
- **Push Mode**: Direct to miner via bore.pub URL
- **Queue Mode**: Redis queue for job distribution
- **Heartbeat System**: Miners report availability every 1-2 seconds
- **Database**: Tracks miners, jobs, metrics

### Performance Optimizations (Latest)
1. **No Deep Copy**: Removed unnecessary menu copying
2. **Single-Pass Execution**: All tools check in one iteration
3. **Skip Intersection**: No complex logic for single tool
4. Result: 10s → 2-3s response time improvement

## Recent Improvements (September 2024)

### Allergen Safety System
1. **Backend Pre-filtering**: Removes unsafe items before AI sees them
2. **Full Ingredient Data**: All items include complete allergen/ingredient lists
3. **Safety Guidelines**: Clear rules to prevent hallucination
4. **Dual Protection**: Backend filters + AI double-checks ingredients

### Fixed Issues
1. **Hallucination**: AI no longer invents allergen information
2. **Inconsistent Responses**: Same query gives consistent safety info
3. **Missing Data**: All search results include full allergen data
4. **Performance**: Optimized from 10s back to 2-3s

## How to Edit/Debug

### To Modify AI Behavior
1. Edit Phase 1 prompt: `build_phase1_prompt()` (Lines 172-275)
2. Edit Phase 2 prompt: `build_phase2_prompt()` (Lines 759-893)
3. Edit safety guidelines: Lines 704-721

### To Add New Tools
1. Add to available tools list in Phase 1 prompt
2. Implement in `execute_tool()` function
3. Add to single-pass execution if search/filter tool

### To Debug Issues
1. Add [DEBUG] to test messages for detailed logs
2. Check `test_results_*/debug_logs/` for full execution details
3. Use fresh client IDs to avoid history interference

### Common Operations
```bash
# Run tests
python3 test_10_clients_sequential.py

# Check database
psql "postgresql://postgres:pEReRSqKEFJGTFSWIlDavmVbxjHQjbBh@shortline.proxy.rlwy.net:31808/railway"

# Deploy changes
git add . && git commit -m "message" && git push origin v3
```

## Key Principles
1. **Never Hallucinate**: Only use data provided, never invent
2. **Safety First**: Pre-filter allergens in backend
3. **Performance Matters**: Single-pass execution, no deep copies
4. **Test Everything**: Use sequential testing with fresh clients
5. **Debug Visibility**: Always include debug info in responses

## Current Status
System is production-ready with:
- Accurate allergen filtering
- Fast response times (2-3s)
- Consistent safety information
- Multi-category support
- Comprehensive test coverage

## Git Information
- Repository: https://github.com/drapeaucharles/restaurant_chat.git
- Main Branch: v3
- Auto-deploys to Railway on push