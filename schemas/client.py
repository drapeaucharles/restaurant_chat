# schemas/client.py

from pydantic import BaseModel
from typing import Dict

class ClientCreateRequest(BaseModel):
    client_id: str
    preferences: Dict[str, str]
