# models.py

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base


# Client Table
class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(String, ForeignKey("restaurants.restaurant_id")) # Added to link clients to restaurants
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())
    preferences = Column(JSON)
    restaurants_visited = Column(JSON)  # list of restaurant_ids
    name = Column(String) # Added for client details
    email = Column(String) # Added for client details
    phone_number = Column(String, nullable=True) # Added for WhatsApp integration

# Restaurant Table
class Restaurant(Base):
    __tablename__ = "restaurants"

    restaurant_id = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="owner")  # options: 'owner', 'staff'
    data = Column(JSON)
    # WhatsApp integration fields
    whatsapp_number = Column(String, nullable=True)  # WhatsApp phone number for this restaurant
    whatsapp_session_id = Column(String, nullable=True)  # Session ID for open-wa
    # Restaurant category (legacy single category field)
    restaurant_category = Column(String, nullable=True, default=None)  # e.g., 'Italian', 'Pizza', 'Pasta', etc.
    # Restaurant categories - PENDING MIGRATION
    # restaurant_categories = Column(JSON, nullable=True, default=list)  # Array of custom categories for this restaurant
    # RAG mode selection for AI chat
    rag_mode = Column(String, nullable=True, default="hybrid_smart_memory")  # Options: 'optimized', 'enhanced_v2', 'enhanced_v3', 'hybrid_smart', 'hybrid_smart_memory'
    # Business type field - commented out until migration runs
    # business_type = Column(String, nullable=True, default="restaurant")  # restaurant, salon, retail, medical, etc.

# ✅ REMOVED: ChatLog model - migrated to ChatMessage only
# ChatLog table preserved in database for rollback safety but removed from Python code

# ChatMessage Table (new, for client-restaurant chat messages)
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(String, ForeignKey("restaurants.restaurant_id"))
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    sender_type = Column(String) # 'client' or 'restaurant'
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())


