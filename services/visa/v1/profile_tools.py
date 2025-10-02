# services/visa/v1/profile_tools.py
"""
Profile management tools for visa agency
Handles customer profile creation, updates, and completeness tracking
"""

import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)


def upsert_partial_profile(db: Session, client_id: str, business_id: str, patch: Dict[str, Any]) -> Dict[str, Any]:
    """
    visa.v1.profile.upsert_partial
    
    Upserts customer profile with partial data
    Idempotent - can be called multiple times with same data
    
    Args:
        client_id: Unique client identifier
        business_id: Business UUID
        patch: Partial profile data to merge
    
    Returns:
        {
            "client_id": str,
            "profile": dict,
            "completeness": float,
            "updated_at": str
        }
    """
    try:
        # Use raw SQL to avoid ORM import issues
        # First, get business UUID from business_id string
        business_uuid_query = text("""
            SELECT id FROM businesses WHERE business_id = :business_id
        """)
        business_result = db.execute(business_uuid_query, {"business_id": business_id}).fetchone()
        
        if not business_result:
            raise ValueError(f"Business not found: {business_id}")
        
        business_uuid = business_result[0]
        
        # Check if lead exists
        lead_query = text("""
            SELECT id, profile_json, updated_at 
            FROM visa_leads 
            WHERE business_id = :business_uuid AND id = :client_id
        """)
        lead_result = db.execute(lead_query, {
            "business_uuid": business_uuid, 
            "client_id": client_id
        }).fetchone()
        
        current_time = datetime.utcnow()
        
        if not lead_result:
            # Create new lead
            insert_query = text("""
                INSERT INTO visa_leads (id, business_id, profile_json, status, created_at, updated_at)
                VALUES (:client_id, :business_uuid, :profile_json, 'new', :current_time, :current_time)
            """)
            db.execute(insert_query, {
                "client_id": client_id,
                "business_uuid": business_uuid,
                "profile_json": json.dumps(patch),
                "current_time": current_time
            })
            final_profile = patch
        else:
            # Merge patch into existing profile
            current_profile = json.loads(lead_result[1]) if lead_result[1] else {}
            current_profile.update(patch)
            final_profile = current_profile
            
            update_query = text("""
                UPDATE visa_leads 
                SET profile_json = :profile_json, updated_at = :current_time
                WHERE id = :client_id AND business_id = :business_uuid
            """)
            db.execute(update_query, {
                "profile_json": json.dumps(final_profile),
                "current_time": current_time,
                "client_id": client_id,
                "business_uuid": business_uuid
            })
        
        db.commit()
        
        # Calculate completeness
        completeness = calculate_profile_completeness(final_profile)
        
        return {
            "client_id": client_id,
            "profile": final_profile,
            "completeness": completeness,
            "updated_at": current_time.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Error upserting profile: {str(e)}")
        db.rollback()
        raise


def calculate_profile_completeness(profile: Dict[str, Any]) -> float:
    """
    Calculate profile completeness as a percentage
    
    Required fields for visa processing:
    - nationality_iso2
    - purpose
    - intended_stay_days
    - earliest_travel_date
    - passport_validity_months
    
    Optional but important:
    - has_return_ticket
    - funds_usd
    - invitation_letter
    """
    required_fields = [
        'nationality_iso2',
        'purpose', 
        'intended_stay_days',
        'earliest_travel_date',
        'passport_validity_months'
    ]
    
    optional_fields = [
        'has_return_ticket',
        'funds_usd',
        'invitation_letter'
    ]
    
    # Count completed required fields (weight: 0.8)
    required_completed = sum(1 for field in required_fields if profile.get(field))
    required_score = (required_completed / len(required_fields)) * 0.8
    
    # Count completed optional fields (weight: 0.2)
    optional_completed = sum(1 for field in optional_fields if profile.get(field))
    optional_score = (optional_completed / len(optional_fields)) * 0.2
    
    return round(required_score + optional_score, 2)


def get_profile_missing_fields(profile: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get missing fields from profile with priority ordering
    
    Returns:
        {
            "missing_required": list,
            "missing_optional": list,
            "next_questions": list  # Top 2 priority questions to ask
        }
    """
    required_fields = {
        'nationality_iso2': 'What is your nationality?',
        'purpose': 'What is the purpose of your visit to Indonesia?',
        'intended_stay_days': 'How many days do you plan to stay?',
        'earliest_travel_date': 'When do you plan to travel?',
        'passport_validity_months': 'How many months is your passport valid for?'
    }
    
    optional_fields = {
        'has_return_ticket': 'Do you have a return ticket?',
        'funds_usd': 'What is your available budget in USD?',
        'invitation_letter': 'Do you have an invitation letter?'
    }
    
    missing_required = [
        {"field": field, "question": question}
        for field, question in required_fields.items()
        if not profile.get(field)
    ]
    
    missing_optional = [
        {"field": field, "question": question}
        for field, question in optional_fields.items()
        if not profile.get(field)
    ]
    
    # Priority order for next questions
    priority_order = [
        'purpose', 'nationality_iso2', 'intended_stay_days', 
        'earliest_travel_date', 'passport_validity_months',
        'has_return_ticket', 'funds_usd', 'invitation_letter'
    ]
    
    all_missing = missing_required + missing_optional
    next_questions = []
    
    for field in priority_order:
        matching = [item for item in all_missing if item["field"] == field]
        if matching:
            next_questions.extend(matching)
        if len(next_questions) >= 2:
            break
    
    return {
        "missing_required": missing_required,
        "missing_optional": missing_optional,
        "next_questions": next_questions[:2]
    }
