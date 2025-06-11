from pydantic import BaseModel, EmailStr
from typing import Optional, Dict
import uuid

class ClientCreateRequest(BaseModel):
    restaurant_id: str
    name: str
    email: Optional[EmailStr] = None
    preferences: Optional[Dict[str, str]] = None

class ClientResponse(BaseModel):
    id: uuid.UUID
    restaurant_id: str
    name: str
    email: Optional[EmailStr] = None
    first_seen: str
    last_seen: str
    preferences: Optional[Dict[str, str]] = None

    class Config:
        orm_mode = True

