# models_universal.py - Universal models for any business type

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean, Float
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from database import Base


# Client Table (works for any business)
class Client(Base):
    __tablename__ = "clients"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(String, ForeignKey("businesses.business_id"))  # Changed from restaurant_id
    first_seen = Column(DateTime(timezone=True), server_default=func.now())
    last_seen = Column(DateTime(timezone=True), onupdate=func.now())
    preferences = Column(JSON)
    businesses_visited = Column(JSON)  # list of business_ids
    name = Column(String)
    email = Column(String)
    phone_number = Column(String, nullable=True)  # For WhatsApp integration
    
    # Additional fields for non-restaurant businesses
    company_name = Column(String, nullable=True)  # For B2B clients
    nationality = Column(String, nullable=True)  # Important for visa services
    requirements = Column(JSON, nullable=True)  # Specific needs/requirements


# Business Table (replaces Restaurant)
class Business(Base):
    __tablename__ = "businesses"

    business_id = Column(String, primary_key=True, index=True)  # Can still be called restaurant_id for compatibility
    password = Column(String, nullable=False)
    role = Column(String, default="owner")  # options: 'owner', 'staff', 'admin'
    data = Column(JSON)  # Business details
    
    # Business type and metadata
    business_type = Column(String, default="restaurant")  # 'restaurant', 'legal_visa', 'salon', 'hotel', etc.
    metadata = Column(JSON, default={})  # Business-specific metadata
    
    # WhatsApp integration fields
    whatsapp_number = Column(String, nullable=True)
    whatsapp_session_id = Column(String, nullable=True)
    
    # Category fields (flexible for any business)
    business_category = Column(String, nullable=True)  # Main category
    business_categories = Column(JSON, nullable=True, default=list)  # Multiple categories
    
    # AI chat configuration
    rag_mode = Column(String, nullable=True, default="memory_universal")
    
    # Backward compatibility
    @property
    def restaurant_id(self):
        return self.business_id
    
    @property
    def restaurant_category(self):
        return self.business_category


# Product Table (replaces MenuItem, works for any product/service)
class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True)
    business_id = Column(String, ForeignKey("businesses.business_id"))
    name = Column(String, nullable=False)
    description = Column(Text)
    price = Column(Float)
    category = Column(String)
    
    # Product type to distinguish different offerings
    product_type = Column(String, default="menu_item")  # 'menu_item', 'service', 'consultation', 'package'
    
    # Additional fields for services
    duration = Column(String, nullable=True)  # "2-3 weeks", "1 hour", etc.
    requirements = Column(JSON, nullable=True)  # Required documents, prerequisites
    features = Column(JSON, nullable=True)  # What's included
    
    # Common fields
    available = Column(Boolean, default=True)
    image_url = Column(String, nullable=True)
    tags = Column(JSON, default=list)  # Searchable tags
    
    # Embeddings for similarity search
    name_embedding = Column(JSON, nullable=True)
    description_embedding = Column(JSON, nullable=True)
    tags_embedding = Column(JSON, nullable=True)
    combined_embedding = Column(JSON, nullable=True)
    
    # Backward compatibility
    @property
    def restaurant_id(self):
        return self.business_id


# ChatMessage Table (works for any business)
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(String, ForeignKey("businesses.business_id"))  # Changed from restaurant_id
    client_id = Column(UUID(as_uuid=True), ForeignKey("clients.id"))
    sender_type = Column(String)  # 'client' or 'ai' or 'staff'
    message = Column(Text)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    whatsapp_message_id = Column(String, nullable=True)
    
    # Additional context
    context = Column(JSON, nullable=True)  # Store query context, intent, etc.
    
    # Backward compatibility
    @property
    def restaurant_id(self):
        return self.business_id


# Backward compatibility views/aliases
Restaurant = Business  # Alias for compatibility
MenuItem = Product  # Alias for compatibility