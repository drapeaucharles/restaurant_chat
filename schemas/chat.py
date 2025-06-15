from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    restaurant_id: str
    client_id: uuid.UUID
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
    ai_enabled: Optional[bool] = True  # ✅ Added to support stop/start logic

    class Config:
        orm_mode = True


class ToggleAIRequest(BaseModel):
    restaurant_id: str
    client_id: str
    enabled: bool