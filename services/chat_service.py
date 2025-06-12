
import openai
from sqlalchemy.orm import Session
import models
from pinecone_utils import query_pinecone
from schemas.chat import ChatRequest, ChatResponse
from schemas.restaurant import RestaurantData # Corrected import
from fastapi import HTTPException

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

def format_menu(menu_items):
    return "\n\n".join([
        f"{item['dish']}: {item['description']} Ingredients: {', '.join(item['ingredients'])}. Allergens: {', '.join(item['allergens'])}"
        for item in menu_items
    ])

from fastapi import HTTPException

def chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.restaurant_id == req.restaurant_id).first()
    if not restaurant:
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")

    data = restaurant.data or {}

    try:
        user_prompt = f"""
Customer message: "{req.message}"

Restaurant Info:
- Name: {data.get("name")}
- Story: {data.get("restaurant_story")}
- Opening Hours: {data.get("opening_hours")}
- Contact Info: {data.get("contact_info")}

Menu:
{format_menu(data.get("menu", []))}
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

        answer = response.choices[0].message.content

    except Exception as e:
        print("OpenAI API ERROR:", e)
        raise HTTPException(status_code=500, detail="Failed to process chat. Please try again.")

    # Ensure client exists
    client = db.query(models.Client).filter(models.Client.id == req.client_id).first()
    if not client:
        client = models.Client(id=req.client_id, restaurant_id=req.restaurant_id)
        db.add(client)
        db.commit()
        db.refresh(client)

    # Log chat
    chat_log = models.ChatLog(
        client_id=req.client_id,
        restaurant_id=req.restaurant_id,
        message=req.message,
        answer=answer
    )
    db.add(chat_log)
    db.commit()

    return ChatResponse(answer=answer)
    restaurant = db.query(models.Restaurant).filter(models.Restaurant.restaurant_id == req.restaurant_id).first()
    if not restaurant:
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")

    try:
        user_prompt = f"""
Customer message: "{req.message}"

Restaurant Info:
- Name: {restaurant.name}
- Story: {restaurant.restaurant_story}
- Opening Hours: {restaurant.opening_hours}
- Contact Info: {restaurant.contact_info}

Menu:
{format_menu(restaurant.menu)}
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

        answer = response.choices[0].message.content

    except Exception as e:
        print("OpenAI API ERROR:", e)
        raise HTTPException(status_code=500, detail="Failed to process chat. Please try again.")

    # Ensure client exists
    client = db.query(models.Client).filter(models.Client.id == req.client_id).first()
    if not client:
        client = models.Client(id=req.client_id, restaurant_id=req.restaurant_id)
        db.add(client)
        db.commit()
        db.refresh(client)

    # Log chat
    chat_log = models.ChatLog(
        client_id=req.client_id,
        restaurant_id=req.restaurant_id,
        message=req.message,
        answer=answer
    )
    db.add(chat_log)
    db.commit()

    return ChatResponse(answer=answer)
