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

class OpeningHours(BaseModel):
    monday: Optional[str] = None
    tuesday: Optional[str] = None
    wednesday: Optional[str] = None
    thursday: Optional[str] = None
    friday: Optional[str] = None
    saturday: Optional[str] = None
    sunday: Optional[str] = None

class RestaurantData(BaseModel):
    name: str
    story: Optional[str] = None  # Make optional to handle incomplete data
    menu: List[MenuItem]
    faq: Optional[List[FAQItem]] = None  # Make optional to handle incomplete data
    opening_hours: Optional[str] = None
    contact_info: Optional[str] = None
    restaurant_story: Optional[str] = None  # Alternative field name
    whatsapp_number: Optional[str] = None  # Add WhatsApp number field

class RestaurantDataPartial(BaseModel):
    name: Optional[str] = None
    story: Optional[str] = None
    menu: Optional[List[MenuItem]] = None
    faq: Optional[List[FAQItem]] = None
    opening_hours: Optional[str] = None
    contact_info: Optional[str] = None
    restaurant_story: Optional[str] = None
    whatsapp_number: Optional[str] = None  # ✅ Must be here

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

class RestaurantUpdateRequest(BaseModel):
    data: RestaurantDataPartial

class RestaurantProfileUpdate(BaseModel):
    name: str
    story: Optional[str] = None
    opening_hours: Optional[OpeningHours] = None
    menu: List[MenuItem]
    faq: Optional[List[FAQItem]] = None
    whatsapp_number: Optional[str] = None

