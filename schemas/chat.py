# schemas/chat.py

from pydantic import BaseModel

class ChatRequest(BaseModel):
    restaurant_id: str
    client_id: str
    table_id: str
    message: str

class ChatResponse(BaseModel):
    answer: str
