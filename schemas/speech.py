"""
Speech-to-text related schemas for audio message handling.
"""

from pydantic import BaseModel
from typing import Optional
import uuid


class SpeechToTextRequest(BaseModel):
    client_id: str
    restaurant_id: str
    table_id: Optional[str] = None


class SpeechToTextResponse(BaseModel):
    transcript: str
    ai_response: str

