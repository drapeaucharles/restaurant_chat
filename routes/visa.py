# routes/visa.py
"""
Visa Agency API Routes
New routes for visa vertical - feature-flagged and backwards compatible
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
import logging
import uuid

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


@router.post("/add-comprehensive-products", dependencies=[Depends(check_visa_enabled)])
def add_comprehensive_visa_products(
    business_id: str = "gsi_bali_agency",
    db: Session = Depends(get_db)
):
    """
    Add comprehensive visa products to GSI Bali Agency
    This endpoint adds all major Indonesia visa types including E-KIT, Visa on Arrival, etc.
    """
    try:
        from sqlalchemy import text
        
        # Comprehensive visa products data
        visa_products = [
            # TOURIST VISAS
            ("B211A", "Visit Visa (Tourist)", "Tourist", "Single", 30, 60, False, False, 500000, 7, "30-day tourist visa, extendable once to 60 days total"),
            ("B211B", "Business Visit Visa", "Business", "Single", 60, None, False, True, 1000000, 10, "60-day business visit visa, requires sponsor"),
            ("VOA", "Visa on Arrival", "Tourist", "Single", 30, 30, False, False, 500000, 0, "Available at major airports, extendable once"),
            ("E-KIT", "Electronic Visa (E-KIT)", "Tourist", "Single", 30, 60, False, False, 500000, 3, "Online application, faster processing"),
            
            # LONG-TERM VISAS
            ("B213", "KITAS (Stay Permit)", "Residence", "Multiple", 365, None, True, True, 5000000, 21, "1-year renewable stay permit, requires sponsor"),
            ("VITAS", "Investment Visa", "Investment", "Multiple", 365, None, True, False, 7500000, 30, "For foreign investors, convertible to KITAS"),
            ("IMTA", "Work Permit", "Work", "Multiple", 365, None, False, True, 6000000, 21, "Foreign worker employment permit"),
            
            # SPECIAL PURPOSE VISAS
            ("B211C", "Social/Cultural Visa", "Social", "Single", 60, 180, False, True, 1000000, 10, "For social, cultural, or educational purposes"),
            ("B211D", "Journalist Visa", "Media", "Single", 30, None, False, True, 1000000, 10, "For journalists and media professionals"),
            ("B211E", "Transit Visa", "Transit", "Single", 7, None, False, False, 250000, 3, "For transit through Indonesia"),
            
            # RETIREMENT & SECOND HOME
            ("RETIREMENT", "Retirement Visa", "Retirement", "Multiple", 365, None, True, False, 4000000, 21, "For retirees 55+, renewable annually"),
            ("SECOND_HOME", "Second Home Visa", "Residence", "Multiple", 365, None, True, False, 10000000, 30, "For wealthy individuals, 5-10 year validity"),
            
            # STUDENT & EDUCATION
            ("STUDENT", "Student Visa", "Education", "Multiple", 365, None, True, True, 3000000, 14, "For students enrolled in Indonesian institutions"),
            ("RESEARCH", "Research Visa", "Education", "Single", 180, 365, False, True, 2000000, 14, "For academic research purposes"),
            
            # MEDICAL & HUMANITARIAN
            ("MEDICAL", "Medical Visa", "Medical", "Single", 60, 180, False, True, 1000000, 7, "For medical treatment in Indonesia"),
            ("HUMANITARIAN", "Humanitarian Visa", "Humanitarian", "Single", 30, 90, False, True, 500000, 5, "For humanitarian missions and aid work"),
            
            # DIPLOMATIC & OFFICIAL
            ("DIPLOMATIC", "Diplomatic Visa", "Diplomatic", "Multiple", 365, None, True, False, 0, 7, "For diplomatic personnel and officials"),
            ("OFFICIAL", "Official Visa", "Official", "Multiple", 90, 365, True, False, 0, 7, "For government officials and representatives")
        ]
        
        # Use the correct business UUID for GSI Bali Agency
        # The catalog table uses UUID format, not the string business_id
        business_uuid = "6becb7a9-f82f-4b3a-857e-28108460ee20"
        
        # Get catalog ID - handle both string and UUID business_id
        catalog_query = text("SELECT id FROM catalogs WHERE business_id = :business_id")
        catalog_result = db.execute(catalog_query, {"business_id": business_uuid}).fetchone()
        
        if not catalog_result:
            # Create catalog if it doesn't exist
            catalog_id = str(uuid.uuid4())
            create_catalog_query = text("""
                INSERT INTO catalogs (id, business_id, created_at)
                VALUES (:catalog_id, :business_id, now())
            """)
            db.execute(create_catalog_query, {"catalog_id": catalog_id, "business_id": business_uuid})
            db.commit()
        else:
            catalog_id = catalog_result[0]
        
        # Clear existing visa products
        delete_query = text("DELETE FROM visa_products WHERE catalog_id = :catalog_id")
        db.execute(delete_query, {"catalog_id": catalog_id})
        
        # Insert comprehensive visa products
        added_count = 0
        for product in visa_products:
            product_id = str(uuid.uuid4())
            insert_query = text("""
                INSERT INTO visa_products (
                    id, catalog_id, product_code, name, category, entry_type,
                    first_stay_days, extendable_to_days, convertible, sponsor_needed,
                    gov_fee_idr, processing_sla_days, notes
                ) VALUES (
                    :id, :catalog_id, :product_code, :name, :category, :entry_type,
                    :first_stay_days, :extendable_to_days, :convertible, :sponsor_needed,
                    :gov_fee_idr, :processing_sla_days, :notes
                )
            """)
            
            db.execute(insert_query, {
                "id": product_id,
                "catalog_id": catalog_id,
                "product_code": product[0],
                "name": product[1],
                "category": product[2],
                "entry_type": product[3],
                "first_stay_days": product[4],
                "extendable_to_days": product[5],
                "convertible": product[6],
                "sponsor_needed": product[7],
                "gov_fee_idr": product[8],
                "processing_sla_days": product[9],
                "notes": product[10]
            })
            added_count += 1
        
        db.commit()
        
        return {
            "status": "success",
            "message": f"Added {added_count} comprehensive visa products",
            "business_id": business_uuid,
            "catalog_id": catalog_id,
            "products_added": added_count
        }
        
    except Exception as e:
        logger.error(f"Error adding comprehensive visa products: {str(e)}")
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add comprehensive visa products: {str(e)}"
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
