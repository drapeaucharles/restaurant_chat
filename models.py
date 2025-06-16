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

# Restaurant Table
class Restaurant(Base):
    __tablename__ = "restaurants"

    restaurant_id = Column(String, primary_key=True, index=True)
    password = Column(String, nullable=False)
    role = Column(String, default="owner")  # options: 'owner', 'staff'
    data = Column(JSON)

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


