# models/visa_models.py
"""
Visa Agency Database Models - Additive to existing restaurant system
All models are namespaced and do not modify existing restaurant tables
"""

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Text, Boolean, Integer, BigInteger
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
import uuid
from database import Base


class Business(Base):
    """
    Extended business table - additive to existing Restaurant table
    Supports multiple business types including restaurants and visa agencies
    """
    __tablename__ = "businesses"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(String, unique=True, index=True)  # e.g., 'bella_vista_restaurant', 'jakarta_visa_agency'
    type = Column(String, nullable=False, default='restaurant')  # 'restaurant', 'visa_agency'
    name = Column(String, nullable=False)
    password = Column(String, nullable=False)
    role = Column(String, default="owner")  # options: 'owner', 'staff'
    data = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    policy_packs = relationship("PolicyPack", back_populates="business", cascade="all, delete-orphan")
    catalogs = relationship("Catalog", back_populates="business", cascade="all, delete-orphan")
    visa_leads = relationship("VisaLead", back_populates="business", cascade="all, delete-orphan")


class PolicyPack(Base):
    """
    Policy/country criteria - rules DSL for visa eligibility and requirements
    Each business can have multiple policy packs for different jurisdictions
    """
    __tablename__ = "policy_packs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    jurisdiction = Column(String(16), nullable=False)  # e.g., 'IDN', 'USA', 'SGP'
    version = Column(String(32), nullable=False)  # e.g., '2025-09', '2025-10'
    data_json = Column(JSON, nullable=False)  # Rules DSL as defined in requirements
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    business = relationship("Business", back_populates="policy_packs")

    __table_args__ = (
        # Unique constraint on business_id, jurisdiction, version
        {'schema': None}  # Ensure no schema conflicts
    )


class Catalog(Base):
    """
    Catalog of visa products for a business
    Each business has one catalog containing multiple visa products
    """
    __tablename__ = "catalogs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    business = relationship("Business", back_populates="catalogs")
    visa_products = relationship("VisaProduct", back_populates="catalog", cascade="all, delete-orphan")


class VisaProduct(Base):
    """
    Individual visa products (A1, B1, C1, C10, etc.)
    Each product has specific requirements, fees, and processing times
    """
    __tablename__ = "visa_products"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    catalog_id = Column(UUID(as_uuid=True), ForeignKey("catalogs.id"), nullable=False)
    product_code = Column(String(32), nullable=False)  # A1, B1, C1, C10, C11, E28A...
    name = Column(Text, nullable=False)
    category = Column(String(64), nullable=False)  # tourism | business_event | investment | gov | crew
    entry_type = Column(String(32), nullable=False)  # single | multiple
    first_stay_days = Column(Integer, nullable=False)
    extendable_to_days = Column(Integer, nullable=True)
    convertible = Column(Boolean, default=False)
    sponsor_needed = Column(Boolean, default=False)
    gov_fee_idr = Column(BigInteger, default=0)
    processing_sla_days = Column(Integer, nullable=True)
    notes = Column(Text, nullable=True)

    # Relationships
    catalog = relationship("Catalog", back_populates="visa_products")
    requirements = relationship("VisaRequirement", back_populates="visa_product", cascade="all, delete-orphan")
    eligibilities = relationship("VisaEligibility", back_populates="visa_product", cascade="all, delete-orphan")
    applications = relationship("VisaApplication", back_populates="visa_product")

    __table_args__ = (
        # Unique constraint on catalog_id, product_code
        {'schema': None}
    )


class VisaRequirement(Base):
    """
    Requirements for each visa product
    Stores key-value pairs of requirements (passport_validity, return_ticket, etc.)
    """
    __tablename__ = "visa_requirements"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visa_product_id = Column(UUID(as_uuid=True), ForeignKey("visa_products.id"), nullable=False)
    key = Column(String(64), nullable=False)  # passport_validity, return_ticket, bank_statement_usd, photo_spec...
    value = Column(Text, nullable=False)  # '>=6 months', '>=USD 2000 (3 months)'
    mandatory = Column(Boolean, default=True)

    # Relationships
    visa_product = relationship("VisaProduct", back_populates="requirements")


class VisaEligibility(Base):
    """
    Eligibility criteria for visa products
    Defines which countries/nationalities are eligible for each visa type
    """
    __tablename__ = "visa_eligibilities"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visa_product_id = Column(UUID(as_uuid=True), ForeignKey("visa_products.id"), nullable=False)
    country_whitelist = Column(Text, nullable=True)  # JSON array of ISO2 codes or '*' for all

    # Relationships
    visa_product = relationship("VisaProduct", back_populates="eligibilities")


class VisaLead(Base):
    """
    Visa leads - potential customers who have inquired about visa services
    Stores customer profile and conversation state
    """
    __tablename__ = "visa_leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    business_id = Column(UUID(as_uuid=True), ForeignKey("businesses.id"), nullable=False)
    client_name = Column(Text, nullable=True)
    client_email = Column(Text, nullable=True)
    client_whatsapp = Column(Text, nullable=True)
    profile_json = Column(JSON, default=dict)  # nationality_iso2, purpose, stay_days, etc.
    recommendation_json = Column(JSON, nullable=True)  # AI recommendations and scores
    status = Column(String(32), default='new')  # new|qualified|won|lost
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    business = relationship("Business", back_populates="visa_leads")
    applications = relationship("VisaApplication", back_populates="visa_lead", cascade="all, delete-orphan")


class VisaApplication(Base):
    """
    Visa applications - formal applications submitted by leads
    Tracks document checklist, payments, and application status
    """
    __tablename__ = "visa_applications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    visa_lead_id = Column(UUID(as_uuid=True), ForeignKey("visa_leads.id"), nullable=False)
    visa_product_id = Column(UUID(as_uuid=True), ForeignKey("visa_products.id"), nullable=False)
    checklist_json = Column(JSON, default=list)  # [{key, uploaded, verified, comment}]
    payments_json = Column(JSON, default=list)  # [{amount_idr, type, paid, txid}]
    status = Column(String(32), default='draft')  # draft|docs_pending|submitted|granted|rejected|refunded
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    visa_lead = relationship("VisaLead", back_populates="applications")
    visa_product = relationship("VisaProduct", back_populates="applications")


# Migration compatibility - extend existing Restaurant model
class RestaurantExtension(Base):
    """
    Extension to existing Restaurant table - adds business type field
    This is additive and doesn't modify existing restaurant behavior
    """
    __tablename__ = "restaurant_extensions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    restaurant_id = Column(String, ForeignKey("restaurants.restaurant_id"), unique=True)
    business_type = Column(String, default='restaurant')  # 'restaurant', 'visa_agency'
    created_at = Column(DateTime(timezone=True), server_default=func.now())
