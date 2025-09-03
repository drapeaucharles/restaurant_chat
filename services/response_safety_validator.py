"""
Response Safety Validator
Scalable post-processing for AI responses to ensure safety and quality
No hardcoding - works for any restaurant
"""

import re
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

def post_process_response(response: str, query: str, used_tools: bool, is_dietary: bool) -> str:
    """
    Clean and validate all responses before sending to customer
    
    Args:
        response: The AI's response
        query: The customer's original query
        used_tools: Whether tools were used to generate response
        is_dietary: Whether this is a dietary/allergen query
    
    Returns:
        Cleaned and validated response
    """
    
    # Step 1: Remove repetitive/annoying openings
    response = remove_repetitive_openings(response)
    
    # Step 2: For dietary queries, ensure safety
    if is_dietary:
        # Check if asking about specific dish properties
        if is_specific_dish_query(query):
            response = enforce_specific_dish_tool_usage(query, response, used_tools)
        
        # Detect dangerous unverified claims
        response = detect_and_block_dangerous_claims(query, response)
        
        # Block uncertain language
        response = block_uncertainty_for_dietary(response)
    
    return response.strip()


def remove_repetitive_openings(response: str) -> str:
    """Remove annoying repetitive phrases like 'Oh, you want...'"""
    
    # Patterns to remove at the beginning of responses
    opening_patterns = [
        # "Oh" patterns
        r"^Oh,?\s+you\s+(?:want|need|'re looking for|'re asking about)\s+[^.!?]*[.!?]\s*",
        r"^Oh,?\s+[^.!?]*[.!?]\s*",
        
        # Other repetitive patterns  
        r"^So\s+you\s+(?:want|need|'re looking for)\s+[^.!?]*[.!?]\s*",
        r"^I\s+see\s+you\s+(?:want|need|'re looking for)\s+[^.!?]*[.!?]\s*",
        r"^You\s+(?:want|need|mentioned)\s+[^.!?]*[.!?]\s*Let's\s+",
    ]
    
    cleaned = response
    for pattern in opening_patterns:
        cleaned = re.sub(pattern, "", cleaned, count=1, flags=re.IGNORECASE)
    
    # Also replace mid-sentence occurrences
    replacements = [
        ("Oh, you want ", "For "),
        ("Oh, you need ", "For "),
        ("Oh, you're looking for ", "Looking for "),
    ]
    
    for old, new in replacements:
        cleaned = cleaned.replace(old, new)
    
    return cleaned


def is_specific_dish_query(query: str) -> bool:
    """
    Detect if query is asking about a specific dish's properties
    e.g., "Is the Penne Arrabbiata vegan?"
    """
    query_lower = query.lower()
    
    # Question indicators
    question_words = ['is', 'does', 'can', 'are', 'has', 'contain', 'have']
    has_question = any(word in query_lower for word in question_words)
    
    # Dietary/allergen indicators
    dietary_words = ['vegan', 'dairy', 'nut', 'gluten', 'egg', 'allergy', 
                    'free', 'contain', 'safe', 'suitable']
    has_dietary = any(word in query_lower for word in dietary_words)
    
    # Check for specific item (usually has capital letters)
    words = query.split()
    capitalized_words = [w for w in words if len(w) > 2 and w[0].isupper()]
    has_specific_item = len(capitalized_words) > 0
    
    return has_question and has_dietary and has_specific_item


def enforce_specific_dish_tool_usage(query: str, response: str, used_tools: bool) -> str:
    """
    If asking about specific dish + dietary property, require tool usage
    """
    if not used_tools:
        logger.warning(f"Blocked non-tool response for specific dish query: {query[:50]}...")
        return (
            "I need to check our ingredient database for accurate information "
            "about that specific dish. One moment please while I verify."
        )
    
    return response


def detect_and_block_dangerous_claims(query: str, response: str) -> str:
    """
    Detect when AI makes specific claims about ingredients without verification
    """
    response_lower = response.lower()
    
    # Claims about ingredients
    contains_claims = [
        "contains", "has", "includes", "made with", "prepared with",
        "doesn't contain", "does not contain", "free from", "without",
        "no dairy", "no nuts", "no gluten", "no eggs"
    ]
    
    # High-risk ingredients
    allergen_words = [
        "dairy", "milk", "cheese", "butter", "cream", "lactose",
        "egg", "eggs",
        "nut", "nuts", "peanut", "almond", "walnut", "cashew", "pistachio",
        "gluten", "wheat", "flour",
        "soy", "tofu",
        "fish", "shellfish", "shrimp", "lobster",
        "meat", "pork", "beef", "chicken", "guanciale", "pancetta"
    ]
    
    # Check if making specific claims
    makes_claim = any(claim in response_lower for claim in contains_claims)
    mentions_allergen = any(word in response_lower for word in allergen_words)
    
    # Red flags - seems like AI is guessing
    red_flags = [
        "all pasta", "most pasta", "typically", "usually", "generally",
        "traditional", "authentic", "classic"
    ]
    has_red_flag = any(flag in response_lower for flag in red_flags)
    
    # Data reference indicators (these suggest tool usage)
    data_references = [
        "according to our menu", "our records show", "the ingredients listed",
        "checking our database", "our system shows", "ingredients are:",
        "allergens:"
    ]
    has_data_reference = any(ref in response_lower for ref in data_references)
    
    if makes_claim and mentions_allergen and not has_data_reference:
        if has_red_flag:
            logger.error(f"Blocked response with unverified generalizations")
            return (
                "I need to check the specific ingredients for that dish rather than "
                "making assumptions. Let me verify the exact ingredients for you."
            )
        else:
            logger.warning(f"Response makes claims without clear data reference")
            # Add a safety note
            return response + "\n\nPlease note: For complete allergen information, please verify with our staff."
    
    return response


def block_uncertainty_for_dietary(response: str) -> str:
    """
    Block responses with uncertain language for dietary queries
    """
    uncertain_phrases = [
        "should be", "probably", "i think", "i believe", 
        "seems to be", "appears to be", "most likely", "might be",
        "fairly certain", "pretty sure"
    ]
    
    response_lower = response.lower()
    
    for phrase in uncertain_phrases:
        if phrase in response_lower:
            logger.warning(f"Blocked uncertain response containing '{phrase}'")
            return (
                "I want to provide you with accurate allergen information. "
                "Let me check our ingredient database to give you a definitive answer."
            )
    
    return response


# Optional: Standalone validation function for testing
def validate_response_safety(response: str, query: str, context: dict = None) -> Tuple[bool, str]:
    """
    Validate if a response is safe for a given query
    
    Returns:
        (is_safe, reason_or_cleaned_response)
    """
    used_tools = context.get('used_tools', False) if context else False
    is_dietary = context.get('is_dietary', False) if context else False
    
    try:
        cleaned = post_process_response(response, query, used_tools, is_dietary)
        
        if cleaned != response:
            return True, cleaned
        else:
            return True, response
            
    except Exception as e:
        logger.error(f"Error validating response: {e}")
        return False, "I apologize, but I need to verify that information. Please ask our staff for assistance."