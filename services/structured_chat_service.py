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
    "show_items": [],
    "hide_items": [],
    "highlight_items": [],
    "custom_message": ""
  }
}

Rules for menu filtering:
1. show_items: When user asks to "show me X", list ALL items matching X. This OVERRIDES all previous show_items.
2. hide_items: Items to ADD to the hidden list (only new items to hide, not cumulative)
3. highlight_items: Items to highlight/recommend (MAX 3-5 items only!)
4. custom_message: Your friendly response to the customer (always include this)

IMPORTANT LOGIC:
- show_items: Used when user says "show me dishes with X" - list ALL matching items
- hide_items: Used when user says "I don't eat X" or "I'm allergic to X" - list items to ADD to hidden list
- highlight_items: Used for recommendations within the shown items

Examples:
1. "Show me dishes with fish" → show_items: ["Grilled Salmon", "Sea Bass", "Tuna Steak", ...all fish dishes]
2. "I'm allergic to nuts" → hide_items: ["Roasted Beet Salad", "Gnocchi Gorgonzola", ...items with nuts]
3. "Show me vegetarian options" → show_items: [...all vegetarian dishes], highlight_items: [3-5 best ones]
4. "I don't like cheese" → hide_items: [...items with cheese to ADD to hidden list]

CRITICAL:
- Always return empty arrays for fields you're not updating
- Use EXACT dish names as they appear in the menu (case-sensitive)
- For show_items, include ALL matching dishes
- For hide_items, only include NEW items to hide (frontend handles accumulation)

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
            max_tokens=500  # Reduced since we're limiting highlights to 3-5 items
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
                show_items=menu_update.get('show_items', []),
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
            
            print(f"✅ Structured response: show={menu_update_obj.show_items}, hide={menu_update_obj.hide_items}, highlight={menu_update_obj.highlight_items}")
            
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
                    show_items=[],
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
                show_items=[],
                hide_items=[],
                highlight_items=[],
                custom_message=error_msg
            )
        )