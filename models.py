# models.py

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base

# Client Table
class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())
    preferences = Column(JSON)
    restaurants_visited = Column(JSON)  # list of restaurant_ids

# Restaurant Table
class Restaurant(Base):
    __tablename__ = "restaurants"

    restaurant_id = Column(String, primary_key=True)
    data = Column(JSON)  # store menu, FAQ, story etc. as JSON blob

# ChatLogs Table
class ChatLog(Base):
    __tablename__ = "chat_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    restaurant_id = Column(String, ForeignKey("restaurants.restaurant_id"))
    table_id = Column(String)
    message = Column(String)
    answer = Column(String)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
