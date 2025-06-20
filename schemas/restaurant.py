from pydantic import BaseModel
from typing import List, Optional

class MenuItem(BaseModel):
    dish: str
    price: Optional[str] = None
    ingredients: Optional[List[str]] = None
    description: Optional[str] = None
    allergens: Optional[List[str]] = None
    name: Optional[str] = None  # Allow both 'dish' and 'name' for flexibility

class FAQItem(BaseModel):
    question: str
    answer: str

class RestaurantData(BaseModel):
    name: str
    story: Optional[str] = None  # Make optional to handle incomplete data
    menu: List[MenuItem]
    faq: Optional[List[FAQItem]] = None  # Make optional to handle incomplete data
    opening_hours: Optional[str] = None
    contact_info: Optional[str] = None
    restaurant_story: Optional[str] = None  # Alternative field name
    whatsapp_number: Optional[str] = None  # Add WhatsApp number field

class RestaurantCreateRequest(BaseModel):
    restaurant_id: str
    data: RestaurantData
    password: str  # ✅ Added for authentication
    role: Optional[str] = "owner"  # options: 'owner', 'staff'

class RestaurantLoginRequest(BaseModel):
    restaurant_id: str
    password: str

class StaffCreateRequest(BaseModel):
    restaurant_id: str
    password: str
    data: Optional[RestaurantData] = None  # Staff might not need full restaurant data

    
class RestaurantDataPartial(BaseModel):
    name: Optional[str] = None
    story: Optional[str] = None
    menu: Optional[List[MenuItem]] = None
    faq: Optional[List[FAQItem]] = None
    opening_hours: Optional[str] = None
    contact_info: Optional[str] = None
    restaurant_story: Optional[str] = None
    whatsapp_number: Optional[str] = None  # ✅ Must be here
    
class RestaurantUpdateRequest(BaseModel):
    data: RestaurantDataPartial
    