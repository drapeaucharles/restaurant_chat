# Deployment Instructions for Improved Chat Service

## Current Status
The improved chat service is deployed but NOT activated by default.

## To Enable Improved Chat Service on Railway:

1. Go to your Railway project dashboard
2. Navigate to the Restaurant Backend service
3. Go to Variables tab
4. Add the following environment variable:
   ```
   USE_IMPROVED_CHAT=true
   ```

5. The service will automatically redeploy with the improved chat enabled

## What the Improved Service Does:
- More natural, conversational responses
- Doesn't immediately list menu items for greetings
- Better context understanding
- Supports conversation history
- Dynamic temperature adjustment

## To Test After Enabling:
Visit: https://restaurantfront-production.up.railway.app/chat?restaurant_id=bella_vista_restaurant&table_id=1

Try these messages:
1. "Hello" - Should give a friendly greeting without listing menu
2. "What pasta do you have?" - Should list all pasta items
3. "Bonjour!" - Should respond in French

## Current Issue:
Without the environment variable, it's using the standard MIA service which has the rigid rules that cause pasta to appear in greetings.

## Alternative: Force Improved Service in Code
If you can't set environment variables, update `/routes/chat.py` line 20:
```python
USE_IMPROVED_CHAT = True  # Force to True instead of reading from env
```

Then commit and push to trigger redeployment.