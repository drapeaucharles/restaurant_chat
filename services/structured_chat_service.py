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
You are an AI restaurant assistant focused on helpful, natural interactions. Respond ONLY with valid JSON.

Format (use ALL fields, don't use legacy show_items/hide_items/highlight_items):
{
  "menu_update": {
    "recommended_items": [],      // Top 3-5 recommendations based on preferences
    "avoid_ingredients": [],      // Ingredients to avoid ["cheese", "nuts", "meat"]
    "avoid_reason": "",          // Why avoiding ("doesn't like meat")
    "preference_type": "",       // "dietary", "taste", "health", "explicit"
    "reorder": false,           // Should reorder menu
    "dim_avoided": true,        // Dim items (true) or hide (false)
    "filter_active": false,     // Is filtering active
    "filter_description": "",   // "Avoiding meat"
    "custom_message": ""        // Your conversational response
  }
}

IMPORTANT UX PRINCIPLES:
1. DEFAULT to dimming items, NOT hiding (unless explicitly asked to hide)
2. Be conversational and explain what you're doing
3. Give users control - mention they can change preferences
4. For "I don't like X" → dim items with X, highlight alternatives
5. For "I'm allergic to X" → strongly highlight safe options, dim dangerous ones
6. For "Show me only X" → use filter_active=true, hide others

Example responses:

"I like cheese":
- recommended_items: ["Cheese Pizza", "Mac & Cheese", "Caprese Salad", "Cheesecake"]
- avoid_ingredients: []
- preference_type: "taste"
- custom_message: "Great to hear you enjoy cheese! I've highlighted some of our best cheese dishes for you to enjoy."

"I don't like meat":
- recommended_items: ["Caesar Salad", "Margherita Pizza", "Pasta Primavera", "Vegetable Soup"]
- avoid_ingredients: ["meat", "beef", "chicken", "pork", "lamb", "steak", "bacon", "ham", "turkey", "duck", "veal", "sausage", "prosciutto", "salami", "pepperoni"]
- avoid_reason: "doesn't like meat"
- preference_type: "taste"
- dim_avoided: true
- filter_description: "Avoiding meat"
- custom_message: "I understand you'd prefer to avoid meat. I've highlighted some delicious vegetarian options and dimmed items containing meat. You can still see all items if you change your mind."

IMPORTANT: For broad categories like "meat", include ALL related ingredients (beef, chicken, steak, etc.)

"I'm allergic to nuts":
- avoid_ingredients: ["nuts", "peanuts", "almonds", "cashews"]
- avoid_reason: "nut allergy"
- preference_type: "dietary"
- custom_message: "I've marked all nut-free dishes as safe for you. Items containing nuts are clearly marked but still visible. Please always confirm with staff about allergens."

"Show me only vegetarian":
- filter_active: true
- filter_description: "Vegetarian only"
- custom_message: "I'm showing only vegetarian options. You can see the full menu again by saying 'show all items'."

Be natural, helpful, and maintain user control.
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
    needs_two_pass = IntentClassifier.needs_two_pass_processing(req.message, intent_type, is_complex)
    
    print(f"🎯 Intent: {intent_type}, Complex: {is_complex}, Model: {recommended_model}")
    print(f"📋 Features: {features}, Needs full menu: {needs_full_menu}")
    print(f"🔄 Two-pass needed: {needs_two_pass}")

    try:
        # For two-pass processing, first detect what data is needed
        if needs_two_pass:
            required_data = IntentClassifier.detect_required_data(req.message)
            print(f"📊 Two-pass mode: Required data: {required_data}")
        else:
            required_data = ['all']  # Single pass gets standard data
        
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
        
        # Format relevant items for context - OPTIMIZED BASED ON REQUIRED DATA
        menu_context = ""
        if relevant_items and needs_full_menu:
            menu_lines = []
            for item in relevant_items[:15]:  # Show more items for better coverage
                line = f"- {item['title']}"
                
                # Include data based on what's actually needed
                if 'ingredients' in required_data and item.get('ingredients'):
                    line += f" [Ingredients: {', '.join(item['ingredients'])}]"
                
                if 'allergens' in required_data and item.get('allergens'):
                    line += f" [Allergens: {','.join(item['allergens'])}]"
                
                if 'prices' in required_data:
                    line += f" [{item.get('price', 'N/A')}]"
                
                if 'descriptions' in required_data and item.get('description'):
                    # Add truncated description for context
                    desc = item['description'][:50] + '...' if len(item['description']) > 50 else item['description']
                    line += f" - {desc}"
                
                menu_lines.append(line)
            
            if menu_lines:
                menu_context = "Relevant menu items:\n" + '\n'.join(menu_lines) + "\n"
        
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
        
        # For filter operations, include items with required data
        if intent_type == 'filter' or 'show' in req.message.lower() or 'hide' in req.message.lower():
            # Build item list with only required data
            if 'ingredients' in required_data:
                # Create a compact format with ingredients
                items_with_data = []
                for item in all_menu_items[:50]:  # Limit to prevent token explosion
                    item_name = item.get('title') or item.get('dish', '')
                    ingredients = item.get('ingredients', [])
                    if ingredients:
                        items_with_data.append(f"{item_name}[{','.join(ingredients)}]")
                    else:
                        items_with_data.append(item_name)
                prompt_parts.append(f"All items with ingredients: {'; '.join(items_with_data)}")
            elif 'allergens' in required_data:
                # Format with allergens
                items_with_data = []
                for item in all_menu_items[:50]:
                    item_name = item.get('title') or item.get('dish', '')
                    allergens = item.get('allergens', [])
                    if allergens:
                        items_with_data.append(f"{item_name}[A:{','.join(allergens)}]")
                    else:
                        items_with_data.append(item_name)
                prompt_parts.append(f"All items with allergens: {'; '.join(items_with_data)}")
            else:
                # Just names for simple operations
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
            
            # Debug logging
            print(f"🔍 Raw AI response: {json.dumps(menu_update, indent=2)}")
            
            # Ensure all required fields exist (support both old and new format)
            menu_update_obj = MenuUpdate(
                # Legacy fields
                show_items=menu_update.get('show_items', []),
                hide_items=menu_update.get('hide_items', []),
                highlight_items=menu_update.get('highlight_items', menu_update.get('recommended_items', [])),
                custom_message=menu_update.get('custom_message', 'I can help you explore our menu!'),
                # New fields
                recommended_items=menu_update.get('recommended_items', menu_update.get('highlight_items', [])),
                avoid_ingredients=menu_update.get('avoid_ingredients', []),
                avoid_reason=menu_update.get('avoid_reason'),
                preference_type=menu_update.get('preference_type'),
                reorder=menu_update.get('reorder', False),
                dim_avoided=menu_update.get('dim_avoided', True),
                filter_active=menu_update.get('filter_active', False),
                filter_description=menu_update.get('filter_description')
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
            
            print(f"✅ Structured response (legacy): show={menu_update_obj.show_items}, hide={menu_update_obj.hide_items}, highlight={menu_update_obj.highlight_items}")
            print(f"✅ Structured response (new): avoid={menu_update_obj.avoid_ingredients}, recommend={menu_update_obj.recommended_items}, dim={menu_update_obj.dim_avoided}")
            
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