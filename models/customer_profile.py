"""
Customer Profile Model for Persistent Memory
"""
from sqlalchemy import Column, String, DateTime, JSON, ARRAY, Text, ForeignKey, Integer
from sqlalchemy.sql import func
from database import Base

class CustomerProfile(Base):
    __tablename__ = "customer_profiles"
    
    # Primary identification
    client_id = Column(String, primary_key=True)
    restaurant_id = Column(String, ForeignKey("restaurants.restaurant_id"))
    
    # Basic info
    name = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    email = Column(String, nullable=True)
    
    # Preferences and restrictions
    dietary_restrictions = Column(ARRAY(String), default=[])  # vegetarian, vegan, halal, kosher
    allergies = Column(ARRAY(String), default=[])  # nuts, shellfish, dairy, gluten
    spice_preference = Column(String, default="medium")  # mild, medium, hot, extra hot
    
    # Order data
    favorite_dishes = Column(ARRAY(String), default=[])
    last_order = Column(JSON, nullable=True)
    order_count = Column(Integer, default=0)
    
    # AI Memory
    important_notes = Column(Text, nullable=True)  # "Celebrates anniversary on June 15"
    preferences = Column(JSON, default={})  # {"seating": "booth", "drinks": "no ice"}
    
    # Timestamps
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    last_visit = Column(DateTime, nullable=True)
    
    def to_dict(self):
        return {
            "name": self.name,
            "dietary_restrictions": self.dietary_restrictions,
            "allergies": self.allergies,
            "favorite_dishes": self.favorite_dishes,
            "preferences": self.preferences,
            "order_count": self.order_count
        }