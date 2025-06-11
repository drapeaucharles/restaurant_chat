from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime

class ChatRequest(BaseModel):
    restaurant_id: str
    client_id: uuid.UUID
    table_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    answer: str

class ChatMessageCreate(BaseModel):
    restaurant_id: str
    client_id: uuid.UUID
    sender_type: str # 'client' or 'restaurant'
    message: str

class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: str
    client_id: uuid.UUID
    sender_type: str
    message: str
    timestamp: datetime

    class Config:
        orm_mode = True

