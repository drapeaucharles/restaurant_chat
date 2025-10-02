# routes/visa.py
"""
Visa Agency API Routes
New routes for visa vertical - feature-flagged and backwards compatible
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging

from database import get_db
from config import MIA_VISA_ENABLED
from schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

# Create router with feature flag check
router = APIRouter(tags=["visa"], prefix="/visa")


def check_visa_enabled():
    """Dependency to check if visa functionality is enabled"""
    if not MIA_VISA_ENABLED:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Visa services are not currently available"
        )


@router.post("/leads", dependencies=[Depends(check_visa_enabled)])
def create_visa_lead(
    client_name: Optional[str] = None,
    client_email: Optional[str] = None,
    client_whatsapp: Optional[str] = None,
    business_id: str = None,
    db: Session = Depends(get_db)
):
    """
    Create a new visa lead
    
    Args:
        client_name: Client's full name
        client_email: Client's email address
        client_whatsapp: Client's WhatsApp number
        business_id: Visa agency business ID
    
    Returns:
        Created lead information
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        
        tools = get_visa_tools(db)
        
        # Create lead with initial profile
        import uuid
        client_id = str(uuid.uuid4())
        
        profile_data = {}
        if client_name:
            profile_data['client_name'] = client_name
        if client_email:
            profile_data['client_email'] = client_email
        if client_whatsapp:
            profile_data['client_whatsapp'] = client_whatsapp
        
        result = tools.profile_upsert_partial(client_id, business_id, profile_data)
        
        return {
            "lead_id": client_id,
            "profile": result.get("profile", {}),
            "completeness": result.get("completeness", 0.0),
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Error creating visa lead: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create visa lead"
        )


@router.post("/leads/{lead_id}/evaluate", dependencies=[Depends(check_visa_enabled)])
def evaluate_visa_eligibility(
    lead_id: str,
    business_id: str,
    db: Session = Depends(get_db)
):
    """
    Evaluate visa eligibility for a lead
    
    Args:
        lead_id: Lead UUID
        business_id: Business UUID
    
    Returns:
        Visa options and eligibility assessment
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        from services.visa.v1.policy_tools import normalize_profile_to_case
        
        tools = get_visa_tools(db)
        
        # Get lead profile
        profile_result = tools.profile_upsert_partial(lead_id, business_id, {})
        profile = profile_result.get("profile", {})
        
        # Get policy and normalize
        policy_result = tools.policypack_resolve(business_id)
        policy_data = policy_result.get("data", {})
        
        normalized_result = normalize_profile_to_case(profile, policy_data)
        normalized_case = normalized_result.get("normalized_case", {})
        
        # Evaluate eligibility
        evaluation_result = tools.rules_evaluate(business_id, normalized_case)
        
        return {
            "lead_id": lead_id,
            "profile_completeness": profile_result.get("completeness", 0.0),
            "options": evaluation_result.get("options", []),
            "policy_version": policy_result.get("version", "default")
        }
        
    except Exception as e:
        logger.error(f"Error evaluating visa eligibility: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate visa eligibility"
        )


@router.post("/applications", dependencies=[Depends(check_visa_enabled)])
def create_visa_application(
    lead_id: str,
    business_id: str,
    product_code: str,
    db: Session = Depends(get_db)
):
    """
    Create a new visa application
    
    Args:
        lead_id: Lead UUID
        business_id: Business UUID
        product_code: Visa product code (e.g., 'A1', 'B1')
    
    Returns:
        Created application information
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        
        tools = get_visa_tools(db)
        
        result = tools.application_create(business_id, lead_id, product_code)
        
        return {
            "application_id": result.get("app_id"),
            "product_code": product_code,
            "checklist": result.get("checklist", []),
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Error creating visa application: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create visa application"
        )


@router.post("/applications/{app_id}/upload", dependencies=[Depends(check_visa_enabled)])
def upload_application_document(
    app_id: str,
    document_key: str,
    file_id: str,
    db: Session = Depends(get_db)
):
    """
    Mark a document as uploaded for an application
    
    Args:
        app_id: Application UUID
        document_key: Document type key
        file_id: Uploaded file identifier
    
    Returns:
        Updated checklist and missing documents
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        
        tools = get_visa_tools(db)
        
        result = tools.application_mark_upload(app_id, document_key, file_id)
        
        return {
            "application_id": app_id,
            "document_key": document_key,
            "checklist": result.get("checklist", []),
            "missing": result.get("missing", []),
            "status": "uploaded"
        }
        
    except Exception as e:
        logger.error(f"Error uploading document: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload document"
        )


@router.post("/payments/intent", dependencies=[Depends(check_visa_enabled)])
def create_payment_intent(
    app_id: str,
    payment_type: str,  # 'full', 'government_fee', 'service_fee'
    db: Session = Depends(get_db)
):
    """
    Create a payment intent for an application
    
    Args:
        app_id: Application UUID
        payment_type: Type of payment
    
    Returns:
        Payment intent with paylink
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        
        tools = get_visa_tools(db)
        
        result = tools.payments_intent(app_id, payment_type)
        
        return {
            "payment_intent_id": result.get("payment_intent_id"),
            "paylink": result.get("paylink"),
            "amount_idr": result.get("amount_idr"),
            "expires_at": result.get("expires_at"),
            "status": "created"
        }
        
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create payment intent"
        )


@router.get("/products", dependencies=[Depends(check_visa_enabled)])
def get_visa_products(
    business_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all available visa products for a business
    
    Args:
        business_id: Business UUID
    
    Returns:
        List of available visa products
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        
        tools = get_visa_tools(db)
        
        result = tools.catalog_get_products(business_id)
        
        return {
            "business_id": business_id,
            "products": result.get("products", [])
        }
        
    except Exception as e:
        logger.error(f"Error getting visa products: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get visa products"
        )


@router.get("/applications/{app_id}/status", dependencies=[Depends(check_visa_enabled)])
def get_application_status(
    app_id: str,
    db: Session = Depends(get_db)
):
    """
    Get current status of a visa application
    
    Args:
        app_id: Application UUID
    
    Returns:
        Application status and progress information
    """
    try:
        from services.visa.v1.tools import get_visa_tools
        
        tools = get_visa_tools(db)
        
        result = tools.application_status(app_id)
        
        return {
            "application_id": app_id,
            "stage": result.get("stage"),
            "substatus": result.get("substatus"),
            "progress": result.get("progress", 0.0),
            "next_actions": result.get("next_actions", []),
            "estimated_completion": result.get("estimated_completion"),
            "documents": result.get("documents", {})
        }
        
    except Exception as e:
        logger.error(f"Error getting application status: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get application status"
        )


@router.post("/chat", dependencies=[Depends(check_visa_enabled)])
def visa_chat(
    request: ChatRequest,
    db: Session = Depends(get_db)
):
    """
    Visa agency chat endpoint
    Handles conversations with visa flow orchestration
    
    Args:
        request: Chat request with message, client_id, restaurant_id
    
    Returns:
        AI-generated response for visa inquiries
    """
    try:
        from services.visa_chat_service import visa_chat_service
        
        response = visa_chat_service(request, db)
        
        return response
        
    except Exception as e:
        logger.error(f"Error in visa chat: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process visa chat request"
        )


# Health check endpoint (always available)
@router.get("/health")
def visa_health_check():
    """
    Health check for visa services
    """
    return {
        "service": "visa_agency",
        "status": "available" if MIA_VISA_ENABLED else "disabled",
        "version": "v1"
    }
