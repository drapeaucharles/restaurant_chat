# services/visa/v1/tools.py
"""
Main visa tools interface - exports all visa.v1.* tools
Provides unified interface for visa agency functionality
"""

import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from .profile_tools import upsert_partial_profile, get_profile_missing_fields
from .policy_tools import resolve_policy_pack, normalize_profile_to_case
from .catalog_tools import get_products, get_requirements, get_product_by_code
from .rules_engine import evaluate_eligibility
from .application_tools import (
    create_application, get_application_status, mark_document_uploaded
)
from .payment_tools import create_quote, create_payment_intent, process_payment_webhook

logger = logging.getLogger(__name__)


class VisaToolsV1:
    """
    Visa Tools v1 - Complete toolset for visa agency operations
    All tools are idempotent and follow JSON schema validation
    """
    
    def __init__(self, db: Session):
        self.db = db
    
    # Profile Management Tools
    
    def profile_upsert_partial(self, client_id: str, business_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
        """
        visa.v1.profile.upsert_partial
        Upserts customer profile with partial data
        """
        return upsert_partial_profile(self.db, client_id, business_id, patch)
    
    def profile_get_missing_fields(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get missing fields from profile with priority ordering
        """
        return get_profile_missing_fields(profile)
    
    # Policy Pack Tools
    
    def policypack_resolve(self, business_id: str, country_code: Optional[str] = None, 
                          version: Optional[str] = None) -> Dict[str, Any]:
        """
        visa.v1.policypack.resolve
        Resolves the appropriate policy pack for a business and jurisdiction
        """
        return resolve_policy_pack(self.db, business_id, country_code, version)
    
    def rules_inputs_from_profile(self, profile: Dict[str, Any], policy_pack_id: str) -> Dict[str, Any]:
        """
        visa.v1.rules.inputs_from_profile
        Normalize profile data into standardized case format
        """
        # Get policy data first
        policy_result = resolve_policy_pack(self.db, policy_pack_id)
        policy_data = policy_result.get("data", {})
        
        return normalize_profile_to_case(profile, policy_data)
    
    # Catalog Tools
    
    def catalog_get_products(self, business_id: str) -> Dict[str, Any]:
        """
        visa.v1.catalog.get_products
        Get all visa products for a business
        """
        return get_products(self.db, business_id)
    
    def catalog_get_requirements(self, business_id: str, product_code: str) -> Dict[str, Any]:
        """
        visa.v1.catalog.get_requirements
        Get requirements checklist for a specific visa product
        """
        return get_requirements(self.db, business_id, product_code)
    
    # Rules Engine
    
    def rules_evaluate(self, business_id: str, normalized_case: Dict[str, Any]) -> Dict[str, Any]:
        """
        visa.v1.rules.evaluate
        Evaluate visa eligibility based on normalized case
        """
        # Get policy data
        policy_result = resolve_policy_pack(self.db, business_id)
        policy_data = policy_result.get("data", {})
        
        return evaluate_eligibility(self.db, business_id, normalized_case, policy_data)
    
    # Application Tools
    
    def application_create(self, business_id: str, client_id: str, product_code: str) -> Dict[str, Any]:
        """
        visa.v1.application.create
        Create a new visa application
        """
        return create_application(self.db, business_id, client_id, product_code)
    
    def application_status(self, app_id: str) -> Dict[str, Any]:
        """
        visa.v1.application.status
        Get current status of a visa application
        """
        return get_application_status(self.db, app_id)
    
    def application_mark_upload(self, app_id: str, key: str, file_id: str) -> Dict[str, Any]:
        """
        visa.v1.application.mark_upload
        Mark a document as uploaded in the application checklist
        """
        return mark_document_uploaded(self.db, app_id, key, file_id)
    
    # Payment Tools
    
    def quote_create(self, business_id: str, client_id: str, product_code: str, 
                    add_ons: List[str] = None) -> Dict[str, Any]:
        """
        visa.v1.quote.create
        Create a quote for visa services
        """
        return create_quote(self.db, business_id, client_id, product_code, add_ons)
    
    def payments_intent(self, app_id: str, kind: str) -> Dict[str, Any]:
        """
        visa.v1.payments.intent
        Create a payment intent for an application
        """
        return create_payment_intent(self.db, app_id, kind)
    
    def payments_webhook(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process payment webhook from payment gateway
        """
        return process_payment_webhook(self.db, payment_data)


# Tool registry for easy access
VISA_TOOLS_V1 = {
    "visa.v1.profile.upsert_partial": "profile_upsert_partial",
    "visa.v1.policypack.resolve": "policypack_resolve", 
    "visa.v1.catalog.get_products": "catalog_get_products",
    "visa.v1.rules.inputs_from_profile": "rules_inputs_from_profile",
    "visa.v1.rules.evaluate": "rules_evaluate",
    "visa.v1.catalog.get_requirements": "catalog_get_requirements",
    "visa.v1.quote.create": "quote_create",
    "visa.v1.application.create": "application_create",
    "visa.v1.application.status": "application_status",
    "visa.v1.application.mark_upload": "application_mark_upload",
    "visa.v1.payments.intent": "payments_intent"
}


def get_visa_tools(db: Session) -> VisaToolsV1:
    """
    Get visa tools instance with database session
    """
    return VisaToolsV1(db)


def execute_visa_tool(db: Session, tool_name: str, **kwargs) -> Dict[str, Any]:
    """
    Execute a visa tool by name
    
    Args:
        db: Database session
        tool_name: Tool name (e.g., 'visa.v1.profile.upsert_partial')
        **kwargs: Tool arguments
    
    Returns:
        Tool execution result
    """
    if tool_name not in VISA_TOOLS_V1:
        raise ValueError(f"Unknown visa tool: {tool_name}")
    
    tools = get_visa_tools(db)
    method_name = VISA_TOOLS_V1[tool_name]
    method = getattr(tools, method_name)
    
    return method(**kwargs)
