import openai
import re
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from pinecone_utils import query_pinecone
from schemas.chat import ChatRequest, ChatResponse
from schemas.restaurant import RestaurantData # Corrected import
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
# Import the fallback function from restaurant service
from services.restaurant_service import apply_menu_fallbacks
from services.simple_response_cache import response_cache

system_prompt = """
You are a friendly restaurant assistant. The customer is viewing our complete menu on their screen.

CRITICAL RULES:
1. If an item is NOT in the provided context, it's NOT on our menu - say "We don't have [item], but..."
2. When something isn't available, suggest a similar item from the context if possible
3. ONLY mention items explicitly provided in the context - these are our actual menu items
4. They can see the menu, so don't list everything
5. Be concise and helpful - max 2-3 sentences
6. For ingredients/allergens: only answer if you have the specific info, otherwise say you'll check
"""

def fetch_recent_chat_history(db: Session, client_id: str, restaurant_id: str):
    """
    Fetch recent chat history for context.
    
    Returns messages from the last 60 minutes, maximum of 20 messages,
    sorted chronologically (oldest to newest).
    
    Args:
        db: Database session
        client_id: Client identifier (table ID or WhatsApp ID)
        restaurant_id: Restaurant identifier
        
    Returns:
        List of ChatMessage objects sorted chronologically
    """
    print(f"🔍 Fetching chat history for client {client_id}, restaurant {restaurant_id}")
    
    # Calculate cutoff time (60 minutes ago)
    cutoff_time = datetime.utcnow() - timedelta(minutes=60)
    print(f"📅 Fetching messages since: {cutoff_time}")
    
    # Query messages from the last 60 minutes
    # Filter by client_id (which could be table ID or WhatsApp ID) and restaurant_id
    # Only include client and ai messages (exclude restaurant messages for context)
    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == client_id,
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.timestamp >= cutoff_time,
        models.ChatMessage.sender_type.in_(['client', 'ai'])  # Only client and AI messages for context
    ).order_by(models.ChatMessage.timestamp.asc()).limit(20).all()  # Oldest to newest, max 20
    
    print(f"📋 Found {len(recent_messages)} recent messages for context")
    
    # Log the messages for debugging
    for i, msg in enumerate(recent_messages):
        print(f"   {i+1}. [{msg.sender_type}] {msg.timestamp}: '{msg.message[:50]}...'")
    
    return recent_messages

def filter_essential_messages(messages):
    """
    Filter out non-essential messages to reduce token usage.
    Keeps messages that contain questions, preferences, or important context.
    
    Args:
        messages: List of ChatMessage objects
        
    Returns:
        List of filtered ChatMessage objects
    """
    # Patterns for non-essential messages
    non_essential_patterns = [
        r'^(ok|okay|thanks|thank you|yes|no|yeah|yep|nope|sure|alright|got it|understood|perfect|great|good|nice|cool|awesome)\.?$',
        r'^(hi|hello|hey|bye|goodbye|see you|later)\.?$',
        r'^👍|😊|😄|🙏|✅|👌$',  # Single emojis
        r'^\.$',  # Just a period
        r'^!+$',  # Just exclamation marks
    ]
    
    essential_keywords = [
        'what', 'how', 'when', 'where', 'why', 'which', 'who',
        'allerg', 'gluten', 'vegan', 'vegetarian', 'dairy', 'nut', 'ingredient',
        'spicy', 'mild', 'recommend', 'suggest', 'best', 'popular', 'favorite',
        'price', 'cost', 'expensive', 'cheap', 'budget',
        'don\'t like', 'avoid', 'without', 'no ', 'free from',
        'show', 'filter', 'only', 'menu', 'options', 'dishes',
        '?'  # Questions
    ]
    
    filtered_messages = []
    
    for msg in messages:
        message_lower = msg.message.lower().strip()
        
        # Always keep AI messages (they contain important context)
        if msg.sender_type == 'ai':
            filtered_messages.append(msg)
            continue
            
        # Check if message is non-essential
        is_non_essential = any(re.match(pattern, message_lower, re.IGNORECASE) for pattern in non_essential_patterns)
        
        # Check if message contains essential keywords
        contains_essential = any(keyword in message_lower for keyword in essential_keywords)
        
        # Keep message if it's not non-essential OR if it contains essential keywords
        if not is_non_essential or contains_essential:
            filtered_messages.append(msg)
    
    return filtered_messages

def format_chat_history_for_openai(chat_history):
    """
    Format chat history messages for OpenAI API.
    
    Maps sender_type to OpenAI roles:
    - 'client' -> 'user'
    - 'ai' -> 'assistant'
    
    Args:
        chat_history: List of ChatMessage objects
        
    Returns:
        List of message dictionaries formatted for OpenAI API
    """
    print(f"🔄 Formatting {len(chat_history)} messages for OpenAI context")
    
    formatted_messages = []
    
    for msg in chat_history:
        # Map sender_type to OpenAI roles
        if msg.sender_type == 'client':
            role = 'user'
        elif msg.sender_type == 'ai':
            role = 'assistant'
        else:
            # Skip restaurant messages or unknown types
            print(f"⚠️ Skipping message with sender_type: {msg.sender_type}")
            continue
            
        formatted_message = {
            "role": role,
            "content": msg.message
        }
        formatted_messages.append(formatted_message)
        print(f"   ✅ [{role}]: '{msg.message[:50]}...'")
    
    print(f"📋 Formatted {len(formatted_messages)} messages for OpenAI")
    return formatted_messages

def get_or_create_client(db: Session, client_id: str, restaurant_id: str, phone_number: str = None):
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        try:
            client = models.Client(
                id=client_id, 
                restaurant_id=restaurant_id,
                phone_number=phone_number  # Store phone number for WhatsApp clients
            )
            db.add(client)
            db.commit()
            db.refresh(client)
        except IntegrityError:
            db.rollback()
            client = db.query(models.Client).filter_by(id=client_id).first()
    else:
        # Update phone number if provided and not already set
        if phone_number and not client.phone_number:
            client.phone_number = phone_number
            db.commit()
            db.refresh(client)
    return client

def validate_menu_item(item):
    """Validate that a menu item has all required fields."""
    required_fields = ['name', 'ingredients', 'description', 'price', 'allergens']
    missing_fields = []
    
    for field in required_fields:
        if field not in item:
            missing_fields.append(field)
    
    if missing_fields:
        raise ValueError(f"Menu item missing required fields: {missing_fields}. Item: {item}")
    
    return True

def format_menu_for_context(menu_items, query):
    """Format only relevant menu items based on the query with exact names."""
    if not menu_items:
        return "Menu data unavailable."
    
    query_lower = query.lower()
    relevant_items = []
    all_item_names = []  # Track all actual menu items
    
    # First, collect all menu item names for validation
    for item in menu_items:
        name = item.get('name') or item.get('dish') or item.get('title', '')
        if name:
            all_item_names.append(name)
    
    # Find items relevant to the query
    for item in menu_items:
        try:
            name = item.get('name') or item.get('dish') or item.get('title', '')
            if not name:
                continue
                
            name_lower = name.lower()
            ingredients = item.get('ingredients', [])
            
            # Check if this item is relevant to the query
            is_relevant = (
                name_lower in query_lower or
                any(word in name_lower for word in query_lower.split() if len(word) > 3) or
                any(ing.lower() in query_lower for ing in ingredients if len(ing) > 3)
            )
            
            if is_relevant:
                allergens = item.get('allergens', [])
                # Use EXACT name with ingredients
                item_info = f"[EXACT: {name}]: {', '.join(ingredients[:5])}"
                if allergens and allergens[0] != 'none':
                    item_info += f" (Allergens: {', '.join(allergens)})"
                relevant_items.append(item_info)
                
        except Exception as e:
            continue
    
    # Build context with validation reminder
    context_parts = []
    
    if relevant_items:
        context_parts.append("Relevant menu items: " + "; ".join(relevant_items[:5]))
    
    # Add validation note about available items (only if asking for recommendations)
    if any(word in query_lower for word in ['recommend', 'suggest', 'good', 'best', 'popular', 'try']):
        # Only mention a few items to validate against
        sample_names = all_item_names[:10] if len(all_item_names) > 10 else all_item_names
        context_parts.append(f"VALIDATION: Only these items exist: {', '.join(sample_names)}...")
    
    return "\n".join(context_parts) if context_parts else ""

def format_faq(faq_items):
    """Format FAQ items for OpenAI prompt with defensive checks."""
    if not faq_items:
        return "No FAQ available."
    
    formatted_items = []
    for item in faq_items:
        try:
            # Ensure all required fields exist with fallbacks
            question = item.get('question', 'Question not available')
            answer = item.get('answer', 'Answer not available')
            
            formatted_item = f"Q: {question}\nA: {answer}"
            formatted_items.append(formatted_item)
            
        except Exception as e:
            print(f"Warning: Error formatting FAQ item {item}: {e}")
            # Add a fallback item to prevent complete failure
            formatted_items.append(f"FAQ item (details unavailable): {str(item)[:100]}")
    
    return "\n\n".join(formatted_items)

def chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Handle chat requests with proper error handling and data validation."""
    
    print(f"\n🔍 ===== CHAT_SERVICE CALLED =====")
    print(f"🏪 Restaurant ID: {req.restaurant_id}")
    print(f"👤 Client ID: {req.client_id}")
    print(f"💬 Message: '{req.message}'")
    print(f"🏷️ Sender Type: {req.sender_type}")

    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    if not restaurant:
        print(f"❌ Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")

    print(f"✅ Restaurant found: {restaurant.restaurant_id}")

    # ✅ VERIFIED: AI response blocking logic with comprehensive logging
    from datetime import datetime, timedelta
    
    print(f"🔍 CHECKING IF AI SHOULD RESPOND...")
    print(f"📋 Direct sender_type check: '{req.sender_type}'")
    
    # First check: Direct sender_type validation
    if req.sender_type == 'restaurant':
        print(f"🚫 BLOCKING AI: sender_type is 'restaurant' (staff message)")
        print(f"===== END CHAT_SERVICE (BLOCKED) =====\n")
        return ChatResponse(answer="")
    
    # Second check: Look for recent staff messages (within last 10 seconds) to avoid race conditions
    recent_cutoff = datetime.utcnow() - timedelta(seconds=10)
    print(f"🕐 Checking for recent staff messages since: {recent_cutoff}")
    
    recent_staff_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == req.client_id,
        models.ChatMessage.restaurant_id == req.restaurant_id,
        models.ChatMessage.sender_type == 'restaurant',
        models.ChatMessage.timestamp >= recent_cutoff
    ).order_by(models.ChatMessage.timestamp.desc()).all()
    
    print(f"📋 Found {len(recent_staff_messages)} recent staff messages")
    for i, staff_msg in enumerate(recent_staff_messages):
        print(f"   Staff message {i+1}: '{staff_msg.message[:50]}...' at {staff_msg.timestamp}")
    
    # Check if this message matches any recent staff message
    is_staff_message = any(
        staff_msg.message.strip() == req.message.strip() 
        for staff_msg in recent_staff_messages
    )
    
    if is_staff_message:
        print(f"🚫 BLOCKING AI: Message matches recent staff message")
        print(f"===== END CHAT_SERVICE (BLOCKED) =====\n")
        return ChatResponse(answer="")
    
    print(f"✅ AI RESPONSE ALLOWED: sender_type='{req.sender_type}', no recent staff match")
    
    # Check cache for common queries
    cached_response = response_cache.get(req.restaurant_id, req.message)
    if cached_response:
        print(f"✅ Using cached response for common query")
        # Still need to save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=cached_response
        )
        db.add(new_message)
        db.commit()
        return ChatResponse(answer=cached_response)

    # ✅ Check AI state BEFORE processing - get ai_enabled from Client.preferences
    print(f"🔍 Checking AI enabled state...")
    client = get_or_create_client(db, req.client_id, req.restaurant_id)  # No phone number for regular chat_service calls
    
    # Get ai_enabled from client preferences, default to True if not set
    ai_enabled_state = True  # Default
    if client.preferences:
        ai_enabled_state = client.preferences.get("ai_enabled", True)
    
    print(f"🔍 AI state for client {req.client_id}: ai_enabled = {ai_enabled_state}")
    
    # ✅ If AI is disabled, skip processing and return empty response
    if not ai_enabled_state:
        print("🚫 AI is disabled for this conversation - skipping AI processing")
        print(f"===== END CHAT_SERVICE (AI DISABLED) =====\n")
        return ChatResponse(answer="")  # ✅ Return empty response

    data = restaurant.data or {}

    try:
        # Prepare menu
        menu_items = data.get("menu", [])
        if menu_items:
            try:
                menu_items = apply_menu_fallbacks(menu_items)
                print(f"Applied fallbacks to {len(menu_items)} menu items")
            except Exception as e:
                print(f"Warning: Error applying menu fallbacks: {e}")

        validated_menu = []
        for item in menu_items:
            if isinstance(item, dict):
                validated_item = {
                    'name': item.get('name') or item.get('dish', 'Unknown Dish'),
                    'description': item.get('description', 'No description available'),
                    'ingredients': item.get('ingredients', []),
                    'allergens': item.get('allergens', []),
                    'price': item.get('price', 'Price not available')
                }
                validated_menu.append(validated_item)

        for item in validated_menu:
            if 'allergens' not in item:
                item['allergens'] = []

        # Prepare FAQ
        faq_items = data.get("faq", [])
        print(f"Found {len(faq_items)} FAQ items")

        # Optimize context - user is viewing menu, only provide specific info needed
        query_lower = req.message.lower()
        
        # Check what specific info is needed
        needs_hours = any(term in query_lower for term in ['open', 'close', 'hour', 'when', 'time'])
        needs_contact = any(term in query_lower for term in ['phone', 'call', 'contact', 'email', 'address', 'location'])
        needs_specific_item_info = any(term in query_lower for term in ['ingredient', 'allerg', 'contain', 'made', 'what is', 'tell me about'])
        asking_for_specific_item = any(term in query_lower for term in ['do you have', 'is there', 'any ', 'looking for', 'want '])
        
        # Build minimal context
        context_parts = [f'Customer asks: "{req.message}"']
        context_parts.append("(Customer is viewing the complete menu on their screen)")
        context_parts.append("RULE: Items NOT in this context are NOT on the menu. Suggest similar items when appropriate.")
        
        # Only add specific context if needed
        if needs_hours:
            context_parts.append(f"Hours: {data.get('opening_hours', 'Check with staff')}")
            
        if needs_contact:
            context_parts.append(f"Contact: {data.get('contact_info', 'Ask staff')}")
        
        # Only include specific menu items if asked about them
        if needs_specific_item_info:
            menu_context = format_menu_for_context(validated_menu, req.message)
            if menu_context:
                context_parts.append(menu_context)
        
        # For recommendations or specific item queries, provide relevant menu items
        if any(word in query_lower for word in ['recommend', 'suggest', 'what should', 'what do you', 'best', 'popular', 'favorite', 'good']) or asking_for_specific_item:
            # Provide more menu items for better context
            menu_items_with_category = []
            categories_seen = set()
            
            for item in validated_menu[:20]:  # More items for better alternatives
                name = item.get('name') or item.get('dish', '')
                category = item.get('category', 'Other')
                if name and len(menu_items_with_category) < 15:  # Limit to 15 items
                    if category not in categories_seen:
                        menu_items_with_category.append(f"[{category}] {name}")
                        categories_seen.add(category)
                    else:
                        menu_items_with_category.append(name)
            
            if menu_items_with_category:
                context_parts.append(f"Menu items: {', '.join(menu_items_with_category)}")
                context_parts.append("If asked item isn't listed above, we don't have it.")
        
        # Check for relevant FAQ
        for faq in faq_items[:5]:  # Check first 5 FAQs
            if any(word in query_lower for word in str(faq.get('question', '')).lower().split() if len(word) > 4):
                context_parts.append(f"Info: {faq.get('answer', '')}")
                break  # Only add most relevant FAQ
        
        user_prompt = "\n".join(context_parts)

        # Fetch recent chat history
        recent_history = fetch_recent_chat_history(db, req.client_id, req.restaurant_id)
        
        messages = [{"role": "system", "content": system_prompt}]
        
        # Only include essential recent context (last 3-5 messages)
        if recent_history:
            filtered_history = filter_essential_messages(recent_history[-6:])  # Last 6 messages max
            if filtered_history:
                history_messages = format_chat_history_for_openai(filtered_history)
                messages.extend(history_messages)
        
        messages.append({"role": "user", "content": user_prompt})

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=messages,
            temperature=0.7,
            max_tokens=150
        )

        answer = response.choices[0].message.content.strip()
        
        # Cache the response for common queries
        query_type = response_cache.get_query_type(req.message)
        if query_type in ['hours', 'location', 'contact', 'wifi', 'parking', 'payment']:
            response_cache.set(req.restaurant_id, req.message, answer)

    except Exception as e:
        print("OpenAI API ERROR:", str(e))
        error_msg = "I'm experiencing technical difficulties. Please try again later."
        return ChatResponse(answer=error_msg)


    # ✅ Log AI message to ChatMessage table (this is what the frontend reads)
    new_message = models.ChatMessage(
        restaurant_id=req.restaurant_id,
        client_id=req.client_id,
        sender_type="ai",
        message=answer
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    print("✅ Logged AI response to ChatMessage table")

    # ✅ REMOVED: No longer logging to ChatLog table - using ChatMessage only
    print("✅ AI response processing complete")
    print(f"===== END CHAT_SERVICE =====\n")

    return ChatResponse(answer=answer)
