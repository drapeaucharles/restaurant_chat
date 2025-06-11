# services/chat_service.py

from sqlalchemy.orm import Session
import models
from pinecone_utils import query_pinecone
from schemas.chat import ChatRequest, ChatResponse

def chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    # Query Pinecone with restaurant & client context
    result = query_pinecone(req.restaurant_id, req.client_id, req.message)

    # Very simple response for now
    if result.matches:
        answer = f"I found something related to your request."
    else:
        answer = "I'm not sure, let me check with the staff."

    # ✅ Ensure client exists before logging
    client = db.query(models.Client).filter(models.Client.id == req.client_id).first()
    if not client:
        client = models.Client(
            id=req.client_id,
            restaurant_id=req.restaurant_id
        )
        db.add(client)
        db.commit()
        db.refresh(client)

    # Log chat in DB
    chat_log = models.ChatLog(
        client_id=req.client_id,
        restaurant_id=req.restaurant_id,
        message=req.message,
        answer=answer
    )
    db.add(chat_log)
    db.commit()

    return ChatResponse(answer=answer)
