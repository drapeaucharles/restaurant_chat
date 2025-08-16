# Restaurant-Specific RAG Mode Selection

## Overview

Restaurant owners can now choose their preferred AI chat mode directly from their dashboard. This allows each restaurant to balance between cost efficiency and response quality based on their specific needs.

## Available RAG Modes

### 1. **Smart Hybrid** (Default - Recommended)
- **Icon**: 🧠 + ⚡
- **Description**: Automatically routes queries based on complexity
- **Benefits**:
  - 60% cost savings compared to always using enhanced mode
  - Fast responses for simple queries
  - Quality responses for complex queries
- **Best for**: Most restaurants wanting balanced cost and quality

### 2. **Optimized**
- **Icon**: ⚡
- **Description**: Fast responses with minimal token usage
- **Benefits**:
  - Lowest cost per query
  - Fastest response times
  - Good for straightforward questions
- **Best for**: High-volume restaurants with simple menus

### 3. **Enhanced Quality**
- **Icon**: 🧠
- **Description**: Higher quality responses with better understanding
- **Benefits**:
  - Best response quality
  - Detailed, nuanced answers
  - Better handling of complex queries
- **Best for**: Fine dining or restaurants with complex menus

### 4. **Enhanced with Memory**
- **Icon**: 💾
- **Description**: Premium experience with conversation memory
- **Benefits**:
  - Remembers previous conversation (last 10 messages)
  - Natural follow-up questions
  - Personalized responses based on preferences
- **Best for**: Restaurants wanting premium customer experience

## Implementation Details

### Database Changes

1. **New Column**: `rag_mode` added to restaurants table
   ```sql
   ALTER TABLE restaurants 
   ADD COLUMN IF NOT EXISTS rag_mode VARCHAR(50) DEFAULT 'hybrid_smart';
   ```

2. **Model Update**: Added to Restaurant model
   ```python
   rag_mode = Column(String, nullable=True, default="hybrid_smart")
   ```

### API Endpoints

1. **Get Current Mode**:
   ```
   GET /restaurant/profile
   Response includes: { ..., "rag_mode": "hybrid_smart" }
   ```

2. **Update Mode**:
   ```
   PUT /restaurant/profile
   Body: { ..., "rag_mode": "enhanced_v3" }
   ```

### Frontend Integration

The owner dashboard now includes a visual RAG mode selector with:
- Clear mode descriptions
- Benefits for each mode
- Visual indicators (icons and colors)
- Real-time updates

### Dynamic Chat Routing

The new `/chat` endpoint (`chat_dynamic.py`) automatically:
1. Checks the restaurant's preferred RAG mode
2. Routes to the appropriate service
3. Falls back to hybrid_smart if mode unavailable
4. Logs which mode was used

## Usage Guide

### For Restaurant Owners

1. **Access Settings**: Log into your owner dashboard
2. **Find AI Chat Mode**: Look for the "AI Chat Mode" section
3. **Select Mode**: Click on your preferred mode
4. **Save Changes**: Click the save button
5. **Immediate Effect**: Changes apply immediately to all new chats

### Mode Selection Tips

- **Start with Smart Hybrid**: Good balance for most restaurants
- **Monitor Performance**: Check customer satisfaction
- **Adjust as Needed**: Switch modes anytime
- **Consider Peak Hours**: Maybe use Optimized during rush times

### Cost Comparison (Monthly)

Based on 10,000 queries/month:
- **Optimized Only**: ~$18
- **Smart Hybrid**: ~$26 (recommended)
- **Enhanced Only**: ~$60
- **Enhanced + Memory**: ~$60-70

## Testing

Run the test script to verify functionality:
```bash
python3 test_rag_mode_selection.py
```

This tests:
- Mode storage and retrieval
- Dynamic routing per restaurant
- All 4 modes working correctly
- Conversation memory in v3
- Mode persistence

## Migration Steps

1. **Run Migration**:
   ```bash
   psql $DATABASE_URL < migrations/add_rag_mode_to_restaurants.sql
   ```

2. **Deploy Backend**:
   - Updated models.py
   - New chat_dynamic.py route
   - Updated main.py

3. **Deploy Frontend**:
   - New RAGModeSelector component
   - Updated RestaurantForm
   - Updated types

## Future Enhancements

1. **Analytics**: Track performance metrics per mode
2. **Auto-Optimization**: Suggest best mode based on usage
3. **Time-Based Modes**: Different modes for different times
4. **Custom Routing**: Let owners define their own rules
5. **A/B Testing**: Compare modes automatically

## Troubleshooting

### Mode Not Saving
- Check browser console for errors
- Verify restaurant has permission to update
- Check if rag_mode column exists in database

### Chat Using Wrong Mode
- Check restaurant's rag_mode in database
- Verify chat_dynamic is being used
- Check logs for routing decisions

### Fallback Behavior
If a mode is unavailable:
1. Falls back to hybrid_smart
2. Logs warning
3. Still processes query

## Support

For issues or questions:
- Check logs for routing decisions
- Verify mode availability with GET /provider
- Test with different modes to isolate issues