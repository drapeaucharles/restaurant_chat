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

    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    if not restaurant:
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")

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

    # Ensure client exists
    client = db.query(models.Client).filter(models.Client.id == req.client_id).first()
    if not client:
        client = models.Client(id=req.client_id, restaurant_id=req.restaurant_id)
        db.add(client)
        db.commit()
        db.refresh(client)

    # ✅ Log chat (only once, after answer is ready)
    chat_log = models.ChatLog(
        client_id=req.client_id,
        restaurant_id=req.restaurant_id,
        table_id=getattr(req, "table_id", "T1"),
        message=req.message,
        answer=answer
    )
    db.add(chat_log)
    db.commit()

    return ChatResponse(answer=answer)
