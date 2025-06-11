from pydantic import BaseModel
from typing import List, Optional

class MenuItem(BaseModel):
    dish: str
    price: str
    ingredients: List[str]
    description: str

class FAQItem(BaseModel):
    question: str
    answer: str

class RestaurantData(BaseModel):
    name: str
    story: str
    menu: List[MenuItem]
    faq: List[FAQItem]

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

