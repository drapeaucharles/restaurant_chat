import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from pinecone_utils import client as openai_client
from schemas.chat import ChatRequest, ChatResponse, MenuUpdate
from services.chat_service import (
    get_or_create_client,
    fetch_recent_chat_history,
    format_chat_history_for_openai,
    apply_menu_fallbacks
)

structured_system_prompt = """
You are an AI restaurant assistant that helps customers explore the menu based on their preferences.

You MUST always respond with ONLY valid JSON in this exact format (no other text before or after):
{
  "menu_update": {
    "hide_items": [],
    "highlight_items": [],
    "custom_message": ""
  }
}

Rules for menu filtering:
1. hide_items: Array of EXACT dish names to hide (e.g., ["Grilled Salmon", "Fish Tacos", "Seafood Paella"] for fish allergies)
2. highlight_items: Array of EXACT dish names to recommend
3. custom_message: Your friendly response to the customer (always include this)

IMPORTANT: 
- Use EXACT dish names as they appear in the menu (case-sensitive)
- DO NOT hide entire categories - only hide specific dishes that conflict with dietary needs
- Always scan the entire menu to find ALL dishes that should be hidden

When customers mention:
- Fish/seafood allergies: hide_items should include ALL dishes containing fish/seafood by their exact names
- Vegetarian/vegan: hide_items should include ALL meat/fish dishes by their exact names
- Nut allergies: hide_items should include ALL dishes with nuts, highlight safe options
- Preferences (spicy, mild, etc.): Highlight matching items by exact name
- General questions: Return empty arrays with helpful message

IMPORTANT: Your entire response must be valid JSON only. Do not include any explanatory text.
"""

def structured_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Handle chat requests with structured menu filtering responses."""
    
    print(f"\n🔍 ===== STRUCTURED CHAT SERVICE =====")
    print(f"🏪 Restaurant ID: {req.restaurant_id}")
    print(f"👤 Client ID: {req.client_id}")
    print(f"💬 Message: '{req.message}'")
    print(f"📋 Structured Response: {req.structured_response}")

    # Get restaurant data
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        return ChatResponse(
            answer="I'm sorry, I cannot find information about this restaurant.",
            menu_update=MenuUpdate(
                hide_categories=[],
                highlight_items=[],
                custom_message="I'm sorry, I cannot find information about this restaurant."
            )
        )

    # Check if this is a restaurant/staff message
    if req.sender_type == 'restaurant':
        print(f"🚫 BLOCKING AI: sender_type is 'restaurant' (staff message)")
        return ChatResponse(answer="", menu_update=None)

    # Check AI enabled state
    client = get_or_create_client(db, req.client_id, req.restaurant_id)
    ai_enabled_state = True
    if client.preferences:
        ai_enabled_state = client.preferences.get("ai_enabled", True)
    
    if not ai_enabled_state:
        print("🚫 AI is disabled for this conversation")
        return ChatResponse(answer="", menu_update=None)

    data = restaurant.data or {}

    try:
        # Prepare menu with categories
        menu_items = data.get("menu", [])
        if menu_items:
            menu_items = apply_menu_fallbacks(menu_items)

        # Format menu for context
        menu_by_category = {}
        for item in menu_items:
            category = item.get('category', 'Uncategorized')
            if category not in menu_by_category:
                menu_by_category[category] = []
            
            item_info = {
                'name': item.get('title') or item.get('dish', 'Unknown'),
                'description': item.get('description', ''),
                'ingredients': item.get('ingredients', []),
                'allergens': item.get('allergens', []),
                'price': item.get('price', '')
            }
            menu_by_category[category].append(item_info)

        # Create menu context
        menu_context = "Menu by Category:\n"
        for category, items in menu_by_category.items():
            menu_context += f"\n{category}:\n"
            for item in items:
                menu_context += f"- {item['name']}: {item['description']}"
                if item['allergens']:
                    menu_context += f" (Allergens: {', '.join(item['allergens'])})"
                menu_context += "\n"

        # Prepare user prompt
        user_prompt = f"""
Customer message: "{req.message}"

Restaurant Info:
- Name: {data.get("name", "Restaurant")}
- Categories Available: {', '.join(menu_by_category.keys())}

{menu_context}

FAQ Info:
{chr(10).join([f"Q: {faq.get('question', '')} A: {faq.get('answer', '')}" for faq in data.get('faq', [])])}

Remember to respond in the exact JSON format specified.
"""

        # Get recent chat history
        recent_history = fetch_recent_chat_history(db, req.client_id, req.restaurant_id)
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": structured_system_prompt}]
        
        if recent_history:
            history_messages = format_chat_history_for_openai(recent_history)
            messages.extend(history_messages)
        
        messages.append({"role": "user", "content": user_prompt})

        # Call OpenAI
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=1000  # Increased to handle larger responses with many dish names
        )

        answer_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            # Try to extract JSON if there's extra text
            json_start = answer_text.find('{')
            json_end = answer_text.rfind('}') + 1
            if json_start >= 0 and json_end > json_start:
                json_text = answer_text[json_start:json_end]
            else:
                json_text = answer_text
                
            json_response = json.loads(json_text)
            menu_update = json_response.get('menu_update', {})
            
            # Ensure all required fields exist
            menu_update_obj = MenuUpdate(
                hide_items=menu_update.get('hide_items', []),
                highlight_items=menu_update.get('highlight_items', []),
                custom_message=menu_update.get('custom_message', 'I can help you explore our menu!')
            )
            
            # Save to database
            new_message = models.ChatMessage(
                restaurant_id=req.restaurant_id,
                client_id=req.client_id,
                sender_type="ai",
                message=menu_update_obj.custom_message
            )
            db.add(new_message)
            db.commit()
            
            print(f"✅ Structured response: hide={menu_update_obj.hide_items}, highlight={menu_update_obj.highlight_items}")
            
            return ChatResponse(
                answer=menu_update_obj.custom_message,
                menu_update=menu_update_obj
            )
            
        except (json.JSONDecodeError, KeyError) as e:
            print(f"❌ JSON parsing error: {e}")
            print(f"Raw response: {answer_text}")
            
            # Fallback if JSON parsing fails
            fallback_message = "I understand you have a fish allergy. Let me help you find safe options on our menu."
            
            # Save fallback message
            new_message = models.ChatMessage(
                restaurant_id=req.restaurant_id,
                client_id=req.client_id,
                sender_type="ai",
                message=fallback_message
            )
            db.add(new_message)
            db.commit()
            
            return ChatResponse(
                answer=fallback_message,
                menu_update=MenuUpdate(
                    hide_items=[],  # No default hiding - AI should determine specific items
                    highlight_items=[],
                    custom_message=fallback_message
                )
            )

    except Exception as e:
        print(f"OpenAI API ERROR: {str(e)}")
        error_msg = "I'm experiencing technical difficulties. Please try again later."
        return ChatResponse(
            answer=error_msg,
            menu_update=MenuUpdate(
                hide_items=[],
                highlight_items=[],
                custom_message=error_msg
            )
        )