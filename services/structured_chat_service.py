from pinecone_utils import openai
import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from schemas.chat import ChatRequest, ChatResponse, MenuUpdate
from services.chat_service import (
    get_or_create_client,
    fetch_recent_chat_history,
    format_chat_history_for_openai,
    apply_menu_fallbacks
)

structured_system_prompt = """
You are an AI restaurant assistant that helps customers explore the menu based on their preferences.

You MUST always respond in this exact JSON format:
{
  "menu_update": {
    "hide_categories": [],
    "highlight_items": [],
    "custom_message": ""
  }
}

Rules for menu filtering:
1. hide_categories: List of category names to hide (e.g., ["Seafood", "Meat"] for vegetarians)
2. highlight_items: List of specific dish names to recommend
3. custom_message: Your friendly response to the customer

When customers mention:
- Dietary restrictions (vegetarian, vegan, gluten-free, etc.): Hide conflicting categories
- Allergies: Hide categories or highlight safe items
- Preferences (spicy, mild, etc.): Highlight matching items
- General questions: Return empty lists with helpful message

Categories available: Breakfast, Brunch, Lunch, Dinner, Appetizers, Soups, Salads, Pasta, Meat, Seafood, Vegetarian, Vegan, Dessert

Example responses:
- "I'm vegetarian" → hide_categories: ["Meat", "Seafood"], highlight_items: ["Mushroom Risotto", "Vegetable Curry"]
- "What's your wifi password?" → hide_categories: [], highlight_items: [], custom_message: "Our wifi password is: restaurant2024"
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
        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=300,
            response_format={"type": "json_object"}  # Force JSON response
        )

        answer_text = response.choices[0].message.content.strip()
        
        # Parse JSON response
        try:
            json_response = json.loads(answer_text)
            menu_update = json_response.get('menu_update', {})
            
            # Ensure all required fields exist
            menu_update_obj = MenuUpdate(
                hide_categories=menu_update.get('hide_categories', []),
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
            
            return ChatResponse(
                answer=menu_update_obj.custom_message,
                menu_update=menu_update_obj
            )
            
        except json.JSONDecodeError:
            # Fallback if JSON parsing fails
            return ChatResponse(
                answer=answer_text,
                menu_update=MenuUpdate(
                    hide_categories=[],
                    highlight_items=[],
                    custom_message=answer_text
                )
            )

    except Exception as e:
        print(f"OpenAI API ERROR: {str(e)}")
        error_msg = "I'm experiencing technical difficulties. Please try again later."
        return ChatResponse(
            answer=error_msg,
            menu_update=MenuUpdate(
                hide_categories=[],
                highlight_items=[],
                custom_message=error_msg
            )
        )