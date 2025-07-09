import json
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from pinecone_utils import client as openai_client, search_menu_items, search_relevant_faqs
from schemas.chat import ChatRequest, ChatResponse, MenuUpdate
from services.chat_service import (
    get_or_create_client,
    fetch_recent_chat_history,
    format_chat_history_for_openai,
    apply_menu_fallbacks,
    filter_essential_messages
)
from services.response_cache import response_cache
from services.intent_classifier import IntentClassifier

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
    
    # Check cache first for common queries
    cached_response = response_cache.get(req.restaurant_id, req.message)
    if cached_response:
        print(f"✅ Using cached response")
        return ChatResponse(
            answer=cached_response.get('answer', ''),
            menu_update=cached_response.get('menu_update')
        )

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
    
    # Classify intent to optimize processing
    intent_type, is_complex, features = IntentClassifier.classify_intent(req.message)
    recommended_model = IntentClassifier.get_model_recommendation(intent_type, is_complex)
    needs_full_menu = IntentClassifier.needs_full_menu_context(intent_type, req.message)
    
    print(f"🎯 Intent: {intent_type}, Complex: {is_complex}, Model: {recommended_model}")
    print(f"📋 Features: {features}, Needs full menu: {needs_full_menu}")

    try:
        # Use semantic search to find relevant menu items based on the query
        # Adjust search based on intent type
        if intent_type == 'simple' or not needs_full_menu:
            # Skip menu search for simple queries
            relevant_items = []
            print(f"⚡ Skipping menu search for simple query")
        else:
            # Adjust top_k based on complexity
            top_k = 20 if intent_type == 'filter' else (15 if is_complex else 10)
            print(f"🔍 Searching for relevant menu items (top_k={top_k})")
            relevant_items = search_menu_items(req.restaurant_id, req.message, top_k=top_k)
        
        # Get all menu items for complete context (needed for show/hide operations)
        all_menu_items = data.get("menu", [])
        if all_menu_items:
            all_menu_items = apply_menu_fallbacks(all_menu_items)
        
        # Format relevant items for context - COMPRESSED VERSION
        menu_context = ""
        if relevant_items and needs_full_menu:
            # Only include essential info to reduce tokens
            menu_lines = []
            for item in relevant_items[:12]:  # Limit items further
                line = f"- {item['title']}"
                # Only add critical info based on query intent
                if 'allerg' in req.message.lower() and item.get('allergens'):
                    line += f" [A: {','.join(item['allergens'])}]"
                elif 'ingredient' in req.message.lower() and item.get('ingredients'):
                    line += f" [I: {','.join(item['ingredients'][:3])}]"
                elif 'price' in req.message.lower() or 'cost' in req.message.lower():
                    line += f" [{item.get('price', 'N/A')}]"
                menu_lines.append(line)
            
            if menu_lines:
                menu_context = "Relevant items:\n" + '\n'.join(menu_lines) + "\n"
        
        # Create list of all item names for show/hide operations
        all_item_names = [item.get('title') or item.get('dish', '') for item in all_menu_items if item.get('title') or item.get('dish')]

        # Get relevant FAQ items based on the query
        all_faqs = data.get('faq', [])
        relevant_faqs = search_relevant_faqs(req.restaurant_id, req.message, all_faqs, top_k=3)
        
        if relevant_faqs:
            faq_text = chr(10).join([f"Q: {faq.get('question', '')} A: {faq.get('answer', '')}" for faq in relevant_faqs])
            print(f"📚 Found {len(relevant_faqs)} relevant FAQs for the query")
        else:
            faq_text = ""
            print(f"📚 No relevant FAQs found for this query")
        
        # Prepare user prompt - COMPRESSED VERSION
        # Only include necessary context based on intent
        prompt_parts = [f'Query: "{req.message}"']
        
        if needs_full_menu and menu_context:
            prompt_parts.append(menu_context)
        
        # Only include full item list for filter operations
        if intent_type == 'filter' or 'show' in req.message.lower() or 'hide' in req.message.lower():
            prompt_parts.append(f"All items: {', '.join(all_item_names)}")
        
        if faq_text:
            prompt_parts.append(f"FAQ:\n{faq_text}")
            
        user_prompt = '\n\n'.join(prompt_parts)

        # Get recent chat history
        recent_history = fetch_recent_chat_history(db, req.client_id, req.restaurant_id)
        
        # Filter out non-essential messages to reduce tokens
        if recent_history:
            filtered_history = filter_essential_messages(recent_history)
            print(f"📊 History filtering: {len(recent_history)} messages → {len(filtered_history)} essential messages")
        else:
            filtered_history = []
        
        # Prepare messages for OpenAI
        messages = [{"role": "system", "content": structured_system_prompt}]
        
        if filtered_history:
            history_messages = format_chat_history_for_openai(filtered_history)
            messages.extend(history_messages)
        
        messages.append({"role": "user", "content": user_prompt})

        # Call OpenAI with recommended model
        response = openai_client.chat.completions.create(
            model=recommended_model,
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
            
            # Cache the response for common queries
            response_data = {
                'answer': menu_update_obj.custom_message,
                'menu_update': menu_update_obj.dict()
            }
            response_cache.set(req.restaurant_id, req.message, response_data)
            
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