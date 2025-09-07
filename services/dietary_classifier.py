"""
AI-based Dietary Restriction Classifier
Quickly classifies if a message contains allergies/intolerances/dietary preferences
"""

import json
import logging
from typing import Dict, Optional
import requests
from config import MIA_BACKEND_URL

logger = logging.getLogger(__name__)

CLASSIFICATION_PROMPT = """Analyze this message for food restrictions. Return JSON only:
{
  "has_restriction": true/false,
  "type": "allergy"|"intolerance"|"preference"|"dislike"|null,
  "items": ["nuts", "dairy", etc] or []
}

Examples:
"I'm allergic to nuts" → {"has_restriction": true, "type": "allergy", "items": ["nuts"]}
"I'm vegan" → {"has_restriction": true, "type": "preference", "items": ["vegan"]}
"I don't like mushrooms" → {"has_restriction": true, "type": "dislike", "items": ["mushrooms"]}
"What's on the menu?" → {"has_restriction": false, "type": null, "items": []}

Message: """

def classify_dietary_message(message: str) -> Optional[Dict]:
    """
    Use AI to classify if message contains dietary restrictions
    Returns: {"has_restriction": bool, "type": str, "items": list}
    """
    try:
        # Quick AI call with minimal tokens
        prompt = CLASSIFICATION_PROMPT + message
        
        response = requests.post(
            f"{MIA_BACKEND_URL}/v1/chat/completions",
            json={
                "model": "gpt-4o-mini",
                "messages": [
                    {"role": "system", "content": "You are a dietary restriction classifier. Return only valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0,
                "max_tokens": 100,
                "response_format": {"type": "json_object"}
            },
            timeout=2  # Short timeout for speed
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            classification = json.loads(content)
            
            logger.info(f"DIETARY CLASSIFIER - Message: '{message}' → {classification}")
            return classification
        else:
            logger.error(f"Classification failed: {response.status_code}")
            return None
            
    except Exception as e:
        logger.error(f"Error in dietary classification: {e}")
        # Fallback to not blocking the main flow
        return None

def should_trigger_allergen_safety(classification: Optional[Dict]) -> bool:
    """
    Determine if classification should trigger allergen safety mode
    """
    if not classification:
        return False
        
    # Allergies and intolerances always trigger safety mode
    if classification.get('type') in ['allergy', 'intolerance']:
        return True
        
    # Dietary preferences (vegan, vegetarian, etc) also trigger safety mode
    if classification.get('type') == 'preference' and classification.get('has_restriction'):
        return True
        
    # Dislikes don't trigger full safety mode (just preferences)
    return False