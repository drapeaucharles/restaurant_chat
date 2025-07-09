import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from pinecone_utils import client as openai_client, search_menu_items
from schemas.chat import ChatRequest, ChatResponse, MenuUpdate
from services.chat_service import (
    get_or_create_client,
    fetch_recent_chat_history,
    format_chat_history_for_openai,
    apply_menu_fallbacks
)

structured_system_prompt = """
You are an AI restaurant assistant. Respond ONLY with valid JSON in this format:
{
  "menu_update": {
    "show_items": [],
    "hide_items": [],
    "highlight_items": [],
    "custom_message": ""
  }
}

Rules:
- show_items: ONLY for explicit filtering requests ("show me only X", "filter by X")
- hide_items: For dislikes/allergies ("I don't eat X", "allergic to X")
- highlight_items: For preferences (max 3-5 items, only positive preferences)
- custom_message: Your response (always required)

Key distinctions:
- "What is X?" = informational query → no filtering
- "Show me only X" = filter request → use show_items
- "I don't like X" = preference → use hide_items

Use EXACT item names from the complete list provided.
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
        # Use semantic search to find relevant menu items based on the query
        print(f"🔍 Searching for relevant menu items for query: '{req.message}'")
        relevant_items = search_menu_items(req.restaurant_id, req.message, top_k=15)
        
        # Get all menu items for complete context (needed for show/hide operations)
        all_menu_items = data.get("menu", [])
        if all_menu_items:
            all_menu_items = apply_menu_fallbacks(all_menu_items)
        
        # Format relevant items for context
        menu_context = "Relevant Menu Items:\n"
        if relevant_items:
            # Group by category for better organization
            items_by_category = {}
            for item in relevant_items:
                category = item.get('category', 'Uncategorized')
                if category not in items_by_category:
                    items_by_category[category] = []
                items_by_category[category].append(item)
            
            for category, items in items_by_category.items():
                menu_context += f"\n{category}:\n"
                for item in items:
                    menu_context += f"- {item['title']}: {item['description']}"
                    if item['ingredients']:
                        menu_context += f" (Ingredients: {', '.join(item['ingredients'][:5])}...)"
                    if item['allergens']:
                        menu_context += f" (Allergens: {', '.join(item['allergens'])})"
                    menu_context += f" - {item['price']}\n"
        else:
            # Fallback: if no relevant items found, include a few sample items
            menu_context += "\nNo specific items found matching your query. Here are some menu categories available:\n"
            categories = list(set(item.get('category', 'Other') for item in all_menu_items))[:5]
            menu_context += ", ".join(categories)
        
        # Create list of all item names for show/hide operations
        all_item_names = [item.get('title') or item.get('dish', '') for item in all_menu_items if item.get('title') or item.get('dish')]

        # Prepare user prompt
        user_prompt = f"""
Customer message: "{req.message}"

Restaurant Info:
- Name: {data.get("name", "Restaurant")}

{menu_context}

Complete list of ALL menu items (for show/hide operations):
{', '.join(all_item_names)}

FAQ Info (if relevant to query):
{chr(10).join([f"Q: {faq.get('question', '')} A: {faq.get('answer', '')}" for faq in data.get('faq', [])[:3]]}

Remember to respond in the exact JSON format specified. When using show_items or hide_items, use EXACT item names from the complete list above.
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