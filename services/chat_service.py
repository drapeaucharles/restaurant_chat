import openai
from sqlalchemy.orm import Session
import models
from pinecone_utils import query_pinecone
from schemas.chat import ChatRequest, ChatResponse
from schemas.restaurant import RestaurantData # Corrected import
from fastapi import HTTPException

# Import the fallback function from restaurant service
from services.restaurant_service import apply_menu_fallbacks

system_prompt = """
You are a helpful, friendly, and professional restaurant staff member. You assist customers via chat with questions about food, ingredients, dietary needs, reservations, opening hours, and anything related to the restaurant.

You must:
- Answer based only on the provided restaurant information (menu, story, hours, etc.)
- Use your knowledge of food, allergies, and dietary terms to give helpful replies
- Be honest — if something is not clear or missing, suggest asking the staff
- Never invent fake details or answer beyond the known context
- Never say you are an AI, unless the customer explicitly asks
- You can say "Hi" or "Welcome" if the message is casual like "hello", and you should always try to be helpful even when information is limited.

You sound like a real person working at the restaurant, not a robot. Keep answers short, clear, and polite.
"""

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

def format_menu(menu_items):
    """Format menu items for OpenAI prompt with defensive checks."""
    if not menu_items:
        return "No menu items available."
    
    formatted_items = []
    for item in menu_items:
        try:
            # Ensure all required fields exist with fallbacks
            name = item.get('name') or item.get('dish', 'Unknown Dish')
            description = item.get('description', 'No description available')
            ingredients = item.get('ingredients', [])
            allergens = item.get('allergens', [])
            price = item.get('price', 'Price not available')
            
            # Format ingredients and allergens safely
            ingredients_str = ', '.join(ingredients) if ingredients else 'Not specified'
            allergens_str = ', '.join(allergens) if allergens else 'None listed'
            
            formatted_item = f"{name}: {description} | Ingredients: {ingredients_str} | Allergens: {allergens_str} | Price: {price}"
            formatted_items.append(formatted_item)
            
        except Exception as e:
            print(f"Warning: Error formatting menu item {item}: {e}")
            # Add a fallback item to prevent complete failure
            formatted_items.append(f"Menu item (details unavailable): {str(item)[:100]}")
    
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

    # ✅ Check AI state BEFORE processing - get the latest ai_enabled state for this client
    print(f"🔍 Checking AI enabled state...")
    latest_log = db.query(models.ChatLog).filter(
        models.ChatLog.client_id == req.client_id,
        models.ChatLog.restaurant_id == req.restaurant_id
    ).order_by(models.ChatLog.timestamp.desc()).first()
    
    # Inherit ai_enabled state from previous conversation, default to True if none exists
    ai_enabled_state = latest_log.ai_enabled if latest_log else True
    
    print(f"🔍 AI state for client {req.client_id}: ai_enabled = {ai_enabled_state}")
    
    # ✅ If AI is disabled, skip processing and return empty response
    if not ai_enabled_state:
        print("🚫 AI is disabled for this conversation - skipping AI processing")
        
        # Ensure client exists
        client = db.query(models.Client).filter_by(id=req.client_id, restaurant_id=req.restaurant_id).first()

        if not client:
            client = models.Client(id=req.client_id, restaurant_id=req.restaurant_id)
            db.add(client)
            db.commit()
            db.refresh(client)


        # ✅ Log the message with NO answer and ai_enabled=False
        chat_log = models.ChatLog(
            client_id=req.client_id,
            restaurant_id=req.restaurant_id,
            table_id=getattr(req, "table_id", "T1"),
            message=req.message,
            answer="",  # ✅ Empty answer when AI is disabled
            ai_enabled=False  # ✅ Keep AI disabled
        )
        db.add(chat_log)
        db.commit()
        print("✅ Logged message with empty answer (AI disabled)")
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

        user_prompt = f"""
Customer message: "{req.message}"

Restaurant Info:
- Name: {data.get("name", "Restaurant name not available")}
- Story: {data.get("restaurant_story", "No story available")}
- Opening Hours: {data.get("opening_hours", "Hours not available")}
- Contact Info: {data.get("contact_info", "Contact info not available")}

Menu:
{format_menu(validated_menu)}
"""

        response = openai.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.5,
            max_tokens=300
        )

        answer = response.choices[0].message.content.strip()

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

    chat_log = models.ChatLog(
        client_id=req.client_id,
        restaurant_id=req.restaurant_id,
        table_id=getattr(req, "table_id", "T1"),
        message=req.message,
        answer=answer,
        ai_enabled=True
    )
    db.add(chat_log)
    db.commit()
    print("✅ Saving chat log for client:", req.client_id)
    print("✅ Log content:", chat_log.message, "→", chat_log.answer)
    print(f"✅ AI enabled state: {chat_log.ai_enabled}")


    return ChatResponse(answer=answer)
