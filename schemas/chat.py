from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import uuid
from datetime import datetime
from pydantic import BaseModel


class ChatRequest(BaseModel):
    restaurant_id: str
    client_id: uuid.UUID
    message: str
    sender_type: Optional[str] = 'client'  # ✅ FIXED: Add sender_type with default
    structured_response: Optional[bool] = False  # Flag to request structured response

class MenuUpdate(BaseModel):
    # Legacy fields (kept for backward compatibility)
    show_items: Optional[List[str]] = []  # When provided, ONLY show these items
    hide_items: Optional[List[str]] = []  # Items to hide (cumulative)
    highlight_items: Optional[List[str]] = []  # Items to highlight
    custom_message: str
    
    # New UX approach fields for better user experience
    recommended_items: Optional[List[str]] = []  # Top recommendations
    avoid_ingredients: Optional[List[str]] = []  # Ingredients to avoid (e.g., ["cheese", "nuts"])
    avoid_reason: Optional[str] = None  # Why avoiding (e.g., "dairy intolerance")
    preference_type: Optional[str] = None  # Type: "dietary", "taste", "health", "explicit"
    reorder: Optional[bool] = False  # Should reorder menu
    dim_avoided: Optional[bool] = True  # Dim instead of hide
    filter_active: Optional[bool] = False  # Is a filter active
    filter_description: Optional[str] = None  # Human-readable filter (e.g., "Avoiding cheese")

class ChatResponse(BaseModel):
    answer: str
    menu_update: Optional[MenuUpdate] = None

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