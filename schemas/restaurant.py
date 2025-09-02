from pydantic import BaseModel, Field, validator, root_validator
from typing import List, Optional, Union

class MenuItem(BaseModel):
    # Required fields
    title: str = Field(..., description="Name/title of the dish or drink")
    description: str = Field(..., description="Description of the dish or drink")
    price: str = Field(..., description="Price as string (e.g., '120K IDR', 'AED 65')")
    
    # Optional fields with validation
    info: Optional[str] = Field(None, description="Additional info like pairing tips or origin details")
    category: Optional[str] = Field(None, description="Menu category")
    subcategory: Optional[str] = Field(None, description="Menu subcategory")
    area: Optional[str] = Field(None, description="Restaurant area (e.g., 'Poolside', 'Rooftop')")
    ingredients: Optional[List[str]] = Field(default_factory=list, description="List of ingredients")
    allergens: Optional[List[str]] = Field(default_factory=list, description="List of allergens")
    
    # Legacy fields for backward compatibility
    dish: Optional[str] = Field(None, description="Legacy field - mapped to title")
    name: Optional[str] = Field(None, description="Legacy field - mapped to title")
    
    # Photo URL field
    photo_url: Optional[str] = Field(None, description="URL of the menu item photo")
    
    # Restaurant-defined category
    restaurant_category: Optional[str] = Field(None, description="Restaurant-defined category like Pasta, Pizza, Salads")
    
    # Dietary fields
    is_vegan: Optional[bool] = Field(None, description="True if the item is vegan (no animal products)")
    is_vegetarian: Optional[bool] = Field(None, description="True if the item is vegetarian (no meat/fish)")
    is_gluten_free: Optional[bool] = Field(None, description="True if the item is gluten-free")
    is_dairy_free: Optional[bool] = Field(None, description="True if the item is dairy-free")
    is_nut_free: Optional[bool] = Field(None, description="True if the item is nut-free")
    dietary_tags: Optional[List[str]] = Field(default_factory=list, description="Additional dietary tags (e.g., 'keto', 'paleo', 'halal', 'kosher')")
    
    @root_validator(pre=True)
    def handle_legacy_fields(cls, values):
        """Handle legacy field mapping before validation."""
        # If title is not provided, try to get it from legacy fields
        if not values.get('title'):
            title = values.get('dish') or values.get('name')
            if title:
                values['title'] = title
        
        # Ensure required fields have defaults
        if not values.get('description'):
            values['description'] = 'No description provided'
        
        if not values.get('price'):
            values['price'] = 'N/A'
        
        return values
    
    @validator('category')
    def validate_category(cls, v):
        if v is not None:
            valid_categories = ["Breakfast", "Brunch", "Lunch", "Dinner", "Cocktail/Drink List"]
            if v not in valid_categories:
                raise ValueError(f"Category must be one of: {valid_categories}")
        return v
    
    @validator('subcategory')
    def validate_subcategory(cls, v):
        if v is not None:
            valid_subcategories = ["starter", "main", "dessert"]
            if v not in valid_subcategories:
                raise ValueError(f"Subcategory must be one of: {valid_subcategories}")
        return v
    
    @validator('price', pre=True, always=True)
    def ensure_price_string(cls, v):
        if v is None:
            return "N/A"
        return str(v)
    
    @validator('allergens', pre=True, always=True)
    def ensure_allergens_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return v
    
    @validator('ingredients', pre=True, always=True)
    def ensure_ingredients_list(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            return [v] if v else []
        return v
    
    class Config:
        # Allow extra fields for backward compatibility
        extra = "allow"
        
        # Example for documentation
        json_schema_extra = {
            "example": {
                "title": "Buffalo Ribeye",
                "description": "Grilled buffalo ribeye served with chimichurri and seasonal vegetables.",
                "info": "Pairs well with Malbec. Grass-fed from New Zealand.",
                "category": "Dinner",
                "subcategory": "main",
                "price": "320K IDR",
                "area": "Main Dining",
                "ingredients": [
                    "Buffalo ribeye", "chimichurri", "seasonal vegetables", "olive oil", "garlic"
                ],
                "allergens": ["none"],
                "is_vegan": False,
                "is_vegetarian": False,
                "is_gluten_free": True,
                "is_dairy_free": True,
                "is_nut_free": True,
                "dietary_tags": ["paleo", "keto-friendly"]
            }
        }

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
    restaurant_categories: Optional[List[str]] = None
    rag_mode: Optional[str] = Field(None, description="AI chat mode: 'optimized', 'enhanced_v2', 'enhanced_v3', 'hybrid_smart', 'hybrid_smart_memory'")

