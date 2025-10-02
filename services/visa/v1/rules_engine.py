# services/visa/v1/rules_engine.py
"""
Rules engine for visa eligibility evaluation
Implements the rules DSL for determining visa options and scoring
"""

import json
import logging
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session
from .catalog_tools import get_products, get_product_by_code

logger = logging.getLogger(__name__)


def evaluate_eligibility(db: Session, business_id: str, normalized_case: Dict[str, Any], 
                        policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    visa.v1.rules.evaluate
    
    Evaluate visa eligibility based on normalized case and policy rules
    
    Args:
        business_id: Business UUID
        normalized_case: Normalized customer profile
        policy_data: Policy pack rules
    
    Returns:
        {
            "options": [
                {
                    "product_code": str,
                    "eligibility": str,  # "eligible", "conditional", "blocked"
                    "blocking_reasons": list,
                    "warnings": list,
                    "stay_days": int,
                    "extendable_to_days": int,
                    "convertible": bool,
                    "sponsor_needed": bool,
                    "gov_fee_idr": int,
                    "processing_sla_days": int,
                    "score": float
                }
            ]
        }
    """
    try:
        # Get all available products
        products_result = get_products(db, business_id)
        products = products_result.get("products", [])
        
        if not products:
            return {"options": []}
        
        # Get purpose mapping from policy
        purpose_map = policy_data.get("purpose_map", {})
        user_purpose = normalized_case.get("purpose", "").lower()
        
        # Find applicable product codes for user's purpose
        applicable_codes = []
        for purpose_key, codes in purpose_map.items():
            if purpose_key.lower() in user_purpose or user_purpose in purpose_key.lower():
                applicable_codes.extend(codes)
        
        # If no specific purpose match, consider all products
        if not applicable_codes:
            applicable_codes = [p["product_code"] for p in products]
        
        options = []
        
        for product in products:
            if product["product_code"] not in applicable_codes:
                continue
            
            # Evaluate this product
            evaluation = evaluate_single_product(
                db, business_id, product, normalized_case, policy_data
            )
            
            if evaluation:
                options.append(evaluation)
        
        # Sort by score (highest first)
        options.sort(key=lambda x: x.get("score", 0), reverse=True)
        
        return {"options": options}
        
    except Exception as e:
        logger.error(f"Error evaluating eligibility: {str(e)}")
        raise


def evaluate_single_product(db: Session, business_id: str, product: Dict[str, Any], 
                          normalized_case: Dict[str, Any], policy_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Evaluate eligibility for a single visa product
    """
    try:
        product_code = product["product_code"]
        
        # Check hard blocks first
        blocking_reasons = check_hard_blocks(normalized_case, policy_data)
        
        # Check country eligibility
        nationality = normalized_case.get("nationality", "")
        if not check_country_eligibility(nationality, product_code, policy_data):
            blocking_reasons.append(f"Nationality {nationality} not eligible for {product_code}")
        
        # Check requirements
        requirements_check = check_requirements(normalized_case, product_code, policy_data)
        warnings = requirements_check.get("warnings", [])
        missing_requirements = requirements_check.get("missing", [])
        
        # Determine eligibility status
        if blocking_reasons:
            eligibility = "blocked"
            score = 0.0
        elif missing_requirements:
            eligibility = "conditional"
            score = calculate_score(normalized_case, product_code, policy_data) * 0.7  # Reduced for missing reqs
        else:
            eligibility = "eligible"
            score = calculate_score(normalized_case, product_code, policy_data)
        
        return {
            "product_code": product_code,
            "eligibility": eligibility,
            "blocking_reasons": blocking_reasons,
            "warnings": warnings + [f"Missing: {req}" for req in missing_requirements],
            "stay_days": product["first_stay_days"],
            "extendable_to_days": product.get("extendable_to_days"),
            "convertible": product.get("convertible", False),
            "sponsor_needed": product.get("sponsor_needed", False),
            "gov_fee_idr": product.get("gov_fee_idr", 0),
            "processing_sla_days": product.get("processing_sla_days"),
            "score": round(score, 3)
        }
        
    except Exception as e:
        logger.error(f"Error evaluating product {product.get('product_code', 'unknown')}: {str(e)}")
        return None


def check_hard_blocks(normalized_case: Dict[str, Any], policy_data: Dict[str, Any]) -> List[str]:
    """
    Check hard blocking conditions
    """
    blocks = []
    hard_blocks = policy_data.get("hard_blocks", [])
    
    for block in hard_blocks:
        condition = block.get("if", "")
        reason = block.get("reason", "")
        message = block.get("message", reason)
        
        if evaluate_condition(condition, normalized_case):
            blocks.append(message)
    
    return blocks


def check_country_eligibility(nationality: str, product_code: str, policy_data: Dict[str, Any]) -> bool:
    """
    Check if nationality is eligible for the product
    """
    whitelists = policy_data.get("whitelists", {})
    product_whitelist = whitelists.get(product_code, {})
    eligible_nationalities = product_whitelist.get("nationalities_in", ["*"])
    
    # "*" means all nationalities are eligible
    if "*" in eligible_nationalities:
        return True
    
    # Check if specific nationality is in whitelist
    return nationality.upper() in [n.upper() for n in eligible_nationalities]


def check_requirements(normalized_case: Dict[str, Any], product_code: str, policy_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Check requirements compliance
    """
    requirements = policy_data.get("requirements", {})
    product_requirements = requirements.get(product_code, [])
    
    warnings = []
    missing = []
    
    for req in product_requirements:
        if ">=" in req:
            # Numeric requirement (e.g., "bank_statement_usd>=2000")
            field, threshold = req.split(">=")
            field_value = normalized_case.get(field, 0)
            
            try:
                if float(field_value) < float(threshold):
                    missing.append(f"{field} must be >= {threshold}")
            except (ValueError, TypeError):
                missing.append(f"{field} value required")
        else:
            # Boolean requirement
            if not normalized_case.get(req):
                missing.append(req)
    
    return {
        "warnings": warnings,
        "missing": missing
    }


def calculate_score(normalized_case: Dict[str, Any], product_code: str, policy_data: Dict[str, Any]) -> float:
    """
    Calculate eligibility score for a product
    """
    scoring = policy_data.get("scoring", {})
    
    # Base score
    base_scores = scoring.get("base", {})
    score = base_scores.get(product_code, 0.5)
    
    # Apply bonuses
    bonuses = scoring.get("bonuses", [])
    for bonus in bonuses:
        condition = bonus.get("when", "")
        bonus_values = bonus.get("add", {})
        
        if evaluate_condition(condition, normalized_case):
            score += bonus_values.get(product_code, 0)
    
    # Apply penalties
    penalties = scoring.get("penalties", [])
    for penalty in penalties:
        condition = penalty.get("when", "")
        penalty_values = penalty.get("sub", {})
        
        if evaluate_condition(condition, normalized_case):
            score -= penalty_values.get(product_code, 0)
    
    # Ensure score is between 0 and 1
    return max(0.0, min(1.0, score))


def evaluate_condition(condition: str, normalized_case: Dict[str, Any]) -> bool:
    """
    Evaluate a condition string against normalized case
    Supports basic comparisons like "field < value", "field == value", etc.
    """
    try:
        # Simple condition parsing
        if "<=" in condition:
            field, value = condition.split("<=")
            field_value = normalized_case.get(field.strip(), 0)
            return float(field_value) <= float(value.strip())
        elif ">=" in condition:
            field, value = condition.split(">=")
            field_value = normalized_case.get(field.strip(), 0)
            return float(field_value) >= float(value.strip())
        elif "<" in condition:
            field, value = condition.split("<")
            field_value = normalized_case.get(field.strip(), 0)
            return float(field_value) < float(value.strip())
        elif ">" in condition:
            field, value = condition.split(">")
            field_value = normalized_case.get(field.strip(), 0)
            return float(field_value) > float(value.strip())
        elif "==" in condition:
            field, value = condition.split("==")
            field_value = normalized_case.get(field.strip())
            target_value = value.strip().strip('"\'')
            
            # Handle boolean comparisons
            if target_value.lower() in ['true', 'false']:
                return bool(field_value) == (target_value.lower() == 'true')
            
            return str(field_value) == target_value
        else:
            # Simple field existence check
            return bool(normalized_case.get(condition.strip()))
            
    except (ValueError, TypeError, AttributeError):
        logger.warning(f"Failed to evaluate condition: {condition}")
        return False
