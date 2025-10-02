# services/visa/v1/policy_tools.py
"""
Policy pack management tools for visa agency
Handles policy pack resolution and rules DSL management
"""

import json
import logging
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session
from models.visa_models import PolicyPack, Business

logger = logging.getLogger(__name__)


def resolve_policy_pack(db: Session, business_id: str, country_code: Optional[str] = None, 
                       version: Optional[str] = None) -> Dict[str, Any]:
    """
    visa.v1.policypack.resolve
    
    Resolves the appropriate policy pack for a business and jurisdiction
    
    Args:
        business_id: Business UUID
        country_code: ISO2 country code (defaults to 'IDN' for Indonesia)
        version: Policy version (defaults to latest)
    
    Returns:
        {
            "policy_pack_id": str,
            "jurisdiction": str,
            "version": str,
            "hash": str,
            "data": dict
        }
    """
    try:
        # Default to Indonesia if no country specified
        jurisdiction = country_code or 'IDN'
        
        # Build query
        query = db.query(PolicyPack).filter(
            PolicyPack.business_id == business_id,
            PolicyPack.jurisdiction == jurisdiction
        )
        
        if version:
            query = query.filter(PolicyPack.version == version)
        else:
            # Get latest version
            query = query.order_by(PolicyPack.version.desc())
        
        policy_pack = query.first()
        
        if not policy_pack:
            # Return default policy pack structure
            default_policy = get_default_policy_pack(jurisdiction)
            return {
                "policy_pack_id": None,
                "jurisdiction": jurisdiction,
                "version": "default",
                "hash": "default",
                "data": default_policy
            }
        
        # Calculate hash for caching
        policy_hash = str(hash(json.dumps(policy_pack.data_json, sort_keys=True)))
        
        return {
            "policy_pack_id": str(policy_pack.id),
            "jurisdiction": policy_pack.jurisdiction,
            "version": policy_pack.version,
            "hash": policy_hash,
            "data": policy_pack.data_json
        }
        
    except Exception as e:
        logger.error(f"Error resolving policy pack: {str(e)}")
        raise


def get_default_policy_pack(jurisdiction: str = 'IDN') -> Dict[str, Any]:
    """
    Get default policy pack for a jurisdiction
    This provides baseline rules when no custom policy is configured
    """
    if jurisdiction == 'IDN':
        return {
            "purpose_map": {
                "tourism": ["A1", "B1", "C1"],
                "business_event": ["C10", "C11"],
                "investment": ["E28A", "E28B", "E28C", "E28D", "E28F"],
                "government": ["A2", "A3"],
                "crew": ["C2", "C3"]
            },
            "hard_blocks": [
                {
                    "if": "passport_validity_months < 6",
                    "reason": "passport_validity",
                    "message": "Passport must be valid for at least 6 months"
                },
                {
                    "if": "intended_stay_days > 365",
                    "reason": "stay_too_long",
                    "message": "Stay duration exceeds maximum allowed"
                }
            ],
            "whitelists": {
                "A1": {"nationalities_in": ["*"]},
                "B1": {"nationalities_in": ["*"]},
                "C1": {"nationalities_in": ["*"]},
                "C10": {"nationalities_in": ["*"]},
                "C11": {"nationalities_in": ["*"]}
            },
            "requirements": {
                "A1": ["passport_validity", "photo_spec"],
                "B1": ["passport_validity", "return_ticket", "photo_spec"],
                "C1": ["passport_validity", "bank_statement_usd>=2000", "return_ticket", "photo_spec"],
                "C10": ["passport_validity", "invitation_letter", "photo_spec"],
                "C11": ["passport_validity", "invitation_letter", "return_ticket", "photo_spec"]
            },
            "scoring": {
                "base": {
                    "A1": 0.92,
                    "B1": 0.88,
                    "C1": 0.85,
                    "C10": 0.80,
                    "C11": 0.75
                },
                "bonuses": [
                    {
                        "when": "intended_stay_days <= 30",
                        "add": {"A1": 0.03, "B1": 0.01, "C1": 0.02}
                    },
                    {
                        "when": "has_return_ticket == true",
                        "add": {"A1": 0.02, "B1": 0.03, "C1": 0.01}
                    }
                ],
                "penalties": [
                    {
                        "when": "funds_usd < 2000",
                        "sub": {"C1": 0.35, "C10": 0.20, "C11": 0.25}
                    },
                    {
                        "when": "passport_validity_months < 9",
                        "sub": {"A1": 0.05, "B1": 0.05, "C1": 0.05}
                    }
                ]
            }
        }
    else:
        # Generic policy for other jurisdictions
        return {
            "purpose_map": {
                "tourism": ["TOURIST"],
                "business": ["BUSINESS"],
                "other": ["OTHER"]
            },
            "hard_blocks": [
                {
                    "if": "passport_validity_months < 6",
                    "reason": "passport_validity",
                    "message": "Passport must be valid for at least 6 months"
                }
            ],
            "whitelists": {
                "TOURIST": {"nationalities_in": ["*"]},
                "BUSINESS": {"nationalities_in": ["*"]},
                "OTHER": {"nationalities_in": ["*"]}
            },
            "requirements": {
                "TOURIST": ["passport_validity", "photo_spec"],
                "BUSINESS": ["passport_validity", "invitation_letter", "photo_spec"],
                "OTHER": ["passport_validity", "photo_spec"]
            },
            "scoring": {
                "base": {
                    "TOURIST": 0.85,
                    "BUSINESS": 0.80,
                    "OTHER": 0.75
                },
                "bonuses": [],
                "penalties": []
            }
        }


def normalize_profile_to_case(profile: Dict[str, Any], policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    visa.v1.rules.inputs_from_profile
    
    Normalize profile data into a standardized case format for rule evaluation
    
    Args:
        profile: Customer profile data
        policy_data: Policy pack data for normalization rules
    
    Returns:
        {
            "normalized_case": dict,
            "missing_fields": list,
            "warnings": list
        }
    """
    try:
        normalized = {}
        warnings = []
        missing_fields = []
        
        # Required fields mapping
        field_mappings = {
            'nationality_iso2': 'nationality',
            'purpose': 'purpose',
            'intended_stay_days': 'stay_days',
            'earliest_travel_date': 'travel_date',
            'passport_validity_months': 'passport_validity_months',
            'has_return_ticket': 'has_return_ticket',
            'funds_usd': 'funds_usd',
            'invitation_letter': 'has_invitation'
        }
        
        # Normalize each field
        for profile_key, normalized_key in field_mappings.items():
            value = profile.get(profile_key)
            
            if value is not None:
                # Type conversions and validations
                if normalized_key == 'stay_days':
                    try:
                        normalized[normalized_key] = int(value)
                    except (ValueError, TypeError):
                        warnings.append(f"Invalid stay_days value: {value}")
                        missing_fields.append(profile_key)
                elif normalized_key == 'passport_validity_months':
                    try:
                        normalized[normalized_key] = int(value)
                    except (ValueError, TypeError):
                        warnings.append(f"Invalid passport_validity_months value: {value}")
                        missing_fields.append(profile_key)
                elif normalized_key == 'funds_usd':
                    try:
                        normalized[normalized_key] = float(value)
                    except (ValueError, TypeError):
                        warnings.append(f"Invalid funds_usd value: {value}")
                        normalized[normalized_key] = 0.0
                elif normalized_key in ['has_return_ticket', 'has_invitation']:
                    # Convert to boolean
                    if isinstance(value, bool):
                        normalized[normalized_key] = value
                    elif isinstance(value, str):
                        normalized[normalized_key] = value.lower() in ['true', 'yes', '1', 'y']
                    else:
                        normalized[normalized_key] = bool(value)
                else:
                    # String fields
                    normalized[normalized_key] = str(value).strip()
            else:
                missing_fields.append(profile_key)
        
        return {
            "normalized_case": normalized,
            "missing_fields": missing_fields,
            "warnings": warnings
        }
        
    except Exception as e:
        logger.error(f"Error normalizing profile: {str(e)}")
        raise
