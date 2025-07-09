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
from services.menu_validation_logger import menu_validation_logger

structured_system_prompt = """
You are an AI restaurant assistant focused on helpful, natural interactions. Respond ONLY with valid JSON.

🚨 CRITICAL RULES - ABSOLUTELY NO EXCEPTIONS:
1. You MUST ONLY recommend menu items that EXACTLY match the names provided in the menu
2. NEVER create, invent, modify, or guess dish names (e.g., no "Mac and Cheese" if it's not in the menu)
3. Copy dish names EXACTLY as they appear - character for character, including capitalization
4. If no items match a preference, say so clearly instead of making up items
5. When you receive "All items:" list, those are the ONLY valid item names you can use

VALIDATION REQUIREMENT: Before including any item in recommended_items, verify it exists in the provided menu list.

Format (use ALL fields, don't use legacy show_items/hide_items/highlight_items):
{
  "menu_update": {
    "recommended_items": [],      // ONLY exact menu item names from the provided list
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

MENU ITEM RULES:
- recommended_items MUST contain ONLY exact names from the menu provided
- If you think an item like "Mac and Cheese" exists but it's not in the menu, DO NOT include it
- If the menu has "Macaroni and Cheese", use that exact name, not "Mac and Cheese"
- Empty recommended_items is better than invented items

IMPORTANT UX PRINCIPLES:
1. DEFAULT to dimming items, NOT hiding (unless explicitly asked to hide)
2. Be conversational and explain what you're doing
3. Give users control - mention they can change preferences
4. For "I don't like X" → dim items with X, highlight alternatives
5. For "I'm allergic to X" → strongly highlight safe options, dim dangerous ones
6. For "Show me only X" → use filter_active=true, hide others

Example responses:

"I like cheese":
- recommended_items: [ONLY items from the provided menu that contain cheese - use EXACT names]
- avoid_ingredients: []
- preference_type: "taste"
- custom_message: "Great to hear you enjoy cheese! I've highlighted all our cheese dishes for you to enjoy."

"I don't like meat":
- recommended_items: [ONLY EXACT item names from the menu that don't contain meat]
- avoid_ingredients: ["meat", "beef", "chicken", "pork", "lamb", "steak", "bacon", "ham", "turkey", "duck", "veal", "sausage", "prosciutto", "salami", "pepperoni"]
- avoid_reason: "doesn't like meat"
- preference_type: "taste"
- dim_avoided: true
- filter_description: "Avoiding meat"
- custom_message: "I understand you'd prefer to avoid meat. I've highlighted some delicious vegetarian options and dimmed items containing meat. You can still see all items if you change your mind."

IMPORTANT: 
- For broad categories like "meat", include ALL related ingredients (beef, chicken, steak, etc.)
- For recommended_items, ONLY use EXACT item names that appear in the menu
- NEVER invent dish names like "Mac and Cheese" if they don't exist
- If unsure whether an item exists, DO NOT include it

"I'm allergic to nuts":
- avoid_ingredients: ["nuts", "peanuts", "almonds", "cashews", "walnuts", "pecans", "hazelnuts", "pistachios", "macadamia"]
- avoid_reason: "nut allergy"
- preference_type: "dietary"
- custom_message: "I've marked all nut-free dishes as safe for you. Items containing nuts are clearly marked but still visible. Please always confirm with staff about allergens."

"Show me only vegetarian":
- filter_active: true
- filter_description: "Vegetarian only"
- custom_message: "I'm showing only vegetarian options. You can see the full menu again by saying 'show all items'."

Be natural, helpful, and maintain user control. NEVER invent menu items.
"""

def validate_menu_items_exist(recommended_items: list, all_menu_items: list) -> tuple[list, list]:
    """
    Validate that recommended items actually exist in the menu.
    
    Args:
        recommended_items: List of item names recommended by AI
        all_menu_items: List of all menu item dictionaries
        
    Returns:
        Tuple of (valid_items, invalid_items)
    """
    # Create a set of all valid menu item names (case-insensitive for comparison)
    valid_names = set()
    name_mapping = {}  # Maps lowercase to actual case
    
    for item in all_menu_items:
        # Get the item name (handle multiple possible fields)
        item_name = item.get('title') or item.get('dish') or item.get('name', '')
        if item_name:
            valid_names.add(item_name.lower())
            name_mapping[item_name.lower()] = item_name
    
    valid_items = []
    invalid_items = []
    
    for recommended in recommended_items:
        if isinstance(recommended, str):
            # Check if the item exists (case-insensitive)
            if recommended.lower() in valid_names:
                # Use the correct case from the actual menu
                valid_items.append(name_mapping[recommended.lower()])
            else:
                invalid_items.append(recommended)
                print(f"⚠️ WARNING: AI recommended non-existent item: '{recommended}'")
    
    return valid_items, invalid_items

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
        # For preference queries, we ALWAYS need menu items to recommend
        if intent_type == 'preference' or 'like' in req.message.lower() or 'love' in req.message.lower():
            # Always search menu for preferences to get actual items
            print(f"🔍 Searching menu for preference query")
            relevant_items = search_menu_items(req.restaurant_id, req.message, top_k=50)  # Increased to get all matching items
            needs_full_menu = True  # Override to ensure we have menu context
        elif intent_type == 'simple' or not needs_full_menu:
            # Skip menu search for truly simple queries
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
        
        # CRITICAL: Create explicit menu validation context
        menu_validation_context = f"\n🚨 IMPORTANT: The ONLY valid menu items you can recommend are:\n{', '.join(['\"' + name + '\"' for name in all_item_names])}\n\nNEVER recommend items not in this list!"

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
        
        # ALWAYS include the menu validation context for preference/filter queries
        if intent_type in ['preference', 'filter'] or any(word in req.message.lower() for word in ['like', 'love', 'want', 'show', 'hide', 'only']):
            prompt_parts.append(menu_validation_context)
        
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
            max_tokens=800  # Increased to handle more recommendations without limit
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
            
            # Validate recommended items exist in the menu
            recommended_items_raw = menu_update.get('recommended_items', menu_update.get('highlight_items', []))
            if recommended_items_raw:
                valid_items, invalid_items = validate_menu_items_exist(recommended_items_raw, all_menu_items)
                
                if invalid_items:
                    print(f"❌ AI tried to recommend non-existent items: {invalid_items}")
                    print(f"✅ Valid items found: {valid_items}")
                    
                    # Log this validation error
                    menu_validation_logger.log_invalid_items(
                        restaurant_id=req.restaurant_id,
                        client_id=req.client_id,
                        user_message=req.message,
                        invalid_items=invalid_items,
                        valid_items=valid_items,
                        ai_response=menu_update
                    )
                    
                    # Update the menu_update with only valid items
                    menu_update['recommended_items'] = valid_items
                    if 'highlight_items' in menu_update:
                        menu_update['highlight_items'] = valid_items
                    
                    # Log this as a critical error
                    print(f"🚨 CRITICAL: AI invented menu items despite explicit instructions!")
                    print(f"🚨 Invalid items: {invalid_items}")
                    print(f"🚨 This should not happen - prompt may need further refinement")
            
            # Also validate show_items and hide_items if present
            if menu_update.get('show_items'):
                valid_show, invalid_show = validate_menu_items_exist(menu_update['show_items'], all_menu_items)
                if invalid_show:
                    print(f"❌ AI tried to show non-existent items: {invalid_show}")
                    menu_update['show_items'] = valid_show
            
            if menu_update.get('hide_items'):
                valid_hide, invalid_hide = validate_menu_items_exist(menu_update['hide_items'], all_menu_items)
                if invalid_hide:
                    print(f"❌ AI tried to hide non-existent items: {invalid_hide}")
                    menu_update['hide_items'] = valid_hide
            
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