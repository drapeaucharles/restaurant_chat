# services/visa/v1/application_tools.py
"""
Application management tools for visa agency
Handles visa application creation, document tracking, and status management
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from models.visa_models import VisaApplication, VisaLead, VisaProduct, Catalog

logger = logging.getLogger(__name__)


def create_application(db: Session, business_id: str, client_id: str, product_code: str) -> Dict[str, Any]:
    """
    visa.v1.application.create
    
    Create a new visa application for a client
    
    Args:
        business_id: Business UUID
        client_id: Client/Lead UUID
        product_code: Visa product code
    
    Returns:
        {
            "app_id": str,
            "checklist": [
                {
                    "key": str,
                    "label": str,
                    "uploaded": bool,
                    "verified": bool,
                    "mandatory": bool,
                    "comment": str
                }
            ]
        }
    """
    try:
        # Find the lead
        lead = db.query(VisaLead).filter(
            VisaLead.id == client_id,
            VisaLead.business_id == business_id
        ).first()
        
        if not lead:
            raise ValueError(f"Lead not found: {client_id}")
        
        # Find the product
        catalog = db.query(Catalog).filter(
            Catalog.business_id == business_id
        ).first()
        
        if not catalog:
            raise ValueError(f"No catalog found for business: {business_id}")
        
        product = db.query(VisaProduct).filter(
            VisaProduct.catalog_id == catalog.id,
            VisaProduct.product_code == product_code
        ).first()
        
        if not product:
            raise ValueError(f"Product not found: {product_code}")
        
        # Check if application already exists
        existing_app = db.query(VisaApplication).filter(
            VisaApplication.visa_lead_id == lead.id,
            VisaApplication.visa_product_id == product.id,
            VisaApplication.status.in_(['draft', 'docs_pending', 'submitted'])
        ).first()
        
        if existing_app:
            # Return existing application
            checklist = generate_checklist(db, product.id)
            return {
                "app_id": str(existing_app.id),
                "checklist": checklist
            }
        
        # Create new application
        checklist = generate_checklist(db, product.id)
        
        application = VisaApplication(
            visa_lead_id=lead.id,
            visa_product_id=product.id,
            checklist_json=checklist,
            payments_json=[],
            status='draft'
        )
        
        db.add(application)
        db.commit()
        
        return {
            "app_id": str(application.id),
            "checklist": checklist
        }
        
    except Exception as e:
        logger.error(f"Error creating application: {str(e)}")
        db.rollback()
        raise


def get_application_status(db: Session, app_id: str) -> Dict[str, Any]:
    """
    visa.v1.application.status
    
    Get current status of a visa application
    
    Args:
        app_id: Application UUID
    
    Returns:
        {
            "stage": str,
            "substatus": str,
            "next_actions": list,
            "progress": float,
            "estimated_completion": str,
            "documents": dict
        }
    """
    try:
        application = db.query(VisaApplication).filter(
            VisaApplication.id == app_id
        ).first()
        
        if not application:
            raise ValueError(f"Application not found: {app_id}")
        
        # Calculate progress
        checklist = application.checklist_json or []
        total_items = len(checklist)
        completed_items = sum(1 for item in checklist if item.get("uploaded", False))
        progress = (completed_items / total_items) if total_items > 0 else 0.0
        
        # Determine next actions
        next_actions = get_next_actions(application)
        
        # Estimate completion
        estimated_completion = estimate_completion_date(application)
        
        return {
            "stage": application.status,
            "substatus": get_substatus(application),
            "next_actions": next_actions,
            "progress": round(progress, 2),
            "estimated_completion": estimated_completion,
            "documents": {
                "total": total_items,
                "uploaded": completed_items,
                "verified": sum(1 for item in checklist if item.get("verified", False))
            }
        }
        
    except Exception as e:
        logger.error(f"Error getting application status: {str(e)}")
        raise


def mark_document_uploaded(db: Session, app_id: str, key: str, file_id: str) -> Dict[str, Any]:
    """
    visa.v1.application.mark_upload
    
    Mark a document as uploaded in the application checklist
    
    Args:
        app_id: Application UUID
        key: Document key
        file_id: Uploaded file identifier
    
    Returns:
        {
            "checklist": list,
            "missing": list
        }
    """
    try:
        application = db.query(VisaApplication).filter(
            VisaApplication.id == app_id
        ).first()
        
        if not application:
            raise ValueError(f"Application not found: {app_id}")
        
        # Update checklist
        checklist = application.checklist_json or []
        updated = False
        
        for item in checklist:
            if item.get("key") == key:
                item["uploaded"] = True
                item["file_id"] = file_id
                item["uploaded_at"] = datetime.utcnow().isoformat()
                updated = True
                break
        
        if not updated:
            # Add new item if not in checklist
            checklist.append({
                "key": key,
                "label": key.replace("_", " ").title(),
                "uploaded": True,
                "verified": False,
                "mandatory": True,
                "file_id": file_id,
                "uploaded_at": datetime.utcnow().isoformat()
            })
        
        application.checklist_json = checklist
        application.updated_at = datetime.utcnow()
        
        # Update status if all mandatory documents uploaded
        missing_mandatory = [
            item for item in checklist 
            if item.get("mandatory", True) and not item.get("uploaded", False)
        ]
        
        if not missing_mandatory and application.status == 'draft':
            application.status = 'docs_pending'
        
        db.commit()
        
        return {
            "checklist": checklist,
            "missing": [item["key"] for item in missing_mandatory]
        }
        
    except Exception as e:
        logger.error(f"Error marking document uploaded: {str(e)}")
        db.rollback()
        raise


def generate_checklist(db: Session, product_id: str) -> List[Dict[str, Any]]:
    """
    Generate document checklist for a visa product
    """
    # Import here to avoid circular imports
    from models.visa_models import VisaRequirement
    
    requirements = db.query(VisaRequirement).filter(
        VisaRequirement.visa_product_id == product_id
    ).all()
    
    checklist = []
    for req in requirements:
        checklist.append({
            "key": req.key,
            "label": req.key.replace("_", " ").title(),
            "uploaded": False,
            "verified": False,
            "mandatory": req.mandatory,
            "spec": req.value,
            "comment": ""
        })
    
    return checklist


def get_next_actions(application: VisaApplication) -> List[str]:
    """
    Get next actions based on application status
    """
    status = application.status
    checklist = application.checklist_json or []
    
    if status == 'draft':
        missing_docs = [
            item["label"] for item in checklist 
            if item.get("mandatory", True) and not item.get("uploaded", False)
        ]
        if missing_docs:
            return [f"Upload {doc}" for doc in missing_docs[:3]]  # Show top 3
        else:
            return ["Review and submit application"]
    
    elif status == 'docs_pending':
        unverified_docs = [
            item["label"] for item in checklist 
            if item.get("uploaded", False) and not item.get("verified", False)
        ]
        if unverified_docs:
            return ["Wait for document verification"]
        else:
            return ["Submit application to immigration office"]
    
    elif status == 'submitted':
        return ["Wait for immigration office processing"]
    
    elif status == 'granted':
        return ["Collect visa from immigration office"]
    
    elif status == 'rejected':
        return ["Contact agent for next steps"]
    
    else:
        return ["Contact agent for assistance"]


def get_substatus(application: VisaApplication) -> str:
    """
    Get detailed substatus based on application state
    """
    status = application.status
    checklist = application.checklist_json or []
    
    if status == 'draft':
        total_docs = len([item for item in checklist if item.get("mandatory", True)])
        uploaded_docs = len([item for item in checklist if item.get("uploaded", False)])
        return f"Documents: {uploaded_docs}/{total_docs}"
    
    elif status == 'docs_pending':
        verified_docs = len([item for item in checklist if item.get("verified", False)])
        total_docs = len(checklist)
        return f"Verification: {verified_docs}/{total_docs}"
    
    elif status == 'submitted':
        # Calculate days since submission
        days_since = (datetime.utcnow() - application.updated_at).days
        return f"Processing day {days_since}"
    
    else:
        return status.replace("_", " ").title()


def estimate_completion_date(application: VisaApplication) -> Optional[str]:
    """
    Estimate completion date based on product SLA and current status
    """
    try:
        product = application.visa_product
        if not product or not product.processing_sla_days:
            return None
        
        if application.status == 'submitted':
            # Estimate from submission date
            completion_date = application.updated_at + timedelta(days=product.processing_sla_days)
        else:
            # Estimate from now (assuming submission soon)
            completion_date = datetime.utcnow() + timedelta(days=product.processing_sla_days + 3)
        
        return completion_date.strftime("%Y-%m-%d")
        
    except Exception:
        return None
