"""
Context Manager - Handles different AI contexts based on customer profile
Dynamically switches between safety, preference, and default contexts
"""

import logging
from typing import Dict, List, Optional, Tuple
from enum import Enum
from sqlalchemy.orm import Session
import models

logger = logging.getLogger(__name__)


class ContextType(Enum):
    """Different context types for AI responses"""
    DEFAULT = "default"
    ALLERGEN_SAFETY = "allergen_safety"
    DIETARY_PREFERENCE = "dietary_preference"
    REGULAR_CUSTOMER = "regular_customer"
    MIXED_RESTRICTIONS = "mixed_restrictions"


class ContextManager:
    """Manages context switching based on customer profile and conversation"""
    
    @staticmethod
    def determine_context(
        customer_profile: Optional[models.CustomerProfile],
        current_message: str,
        conversation_history: List[Dict] = None
    ) -> Tuple[ContextType, Dict[str, any]]:
        """
        Determine which context to use based on customer profile and current conversation
        
        Returns:
            (context_type, context_data)
        """
        
        # Check for context override in current message
        override = ContextManager._check_context_override(current_message)
        if override:
            logger.info(f"Context override detected: {override}")
            return override, {}
        
        # If no profile, use default
        if not customer_profile:
            logger.info("CONTEXT_MANAGER DEBUG - No customer profile provided")
            return ContextType.DEFAULT, {}
        
        # Extract profile data - handle both old and new formats
        profile_data = customer_profile.preferences or {}
        
        # Get allergens from correct location (profile.allergies not preferences['allergens'])
        allergens = customer_profile.allergies or profile_data.get('allergens', [])
        
        # Get dietary preferences from correct location
        dietary_preferences = customer_profile.dietary_restrictions or profile_data.get('dietary_preferences', [])
        
        # DEBUG: Log what we found
        logger.info(f"CONTEXT_MANAGER DEBUG - Profile exists: {customer_profile}")
        logger.info(f"CONTEXT_MANAGER DEBUG - Allergens found: {allergens}")
        logger.info(f"CONTEXT_MANAGER DEBUG - Dietary preferences found: {dietary_preferences}")
        logger.info(f"CONTEXT_MANAGER DEBUG - Profile.allergies: {customer_profile.allergies}")
        logger.info(f"CONTEXT_MANAGER DEBUG - Profile.dietary_restrictions: {customer_profile.dietary_restrictions}")
        logger.info(f"CONTEXT_MANAGER DEBUG - Profile.preferences: {customer_profile.preferences}")
        
        # Determine primary context based on profile
        if allergens:
            # Safety is highest priority
            if len(allergens) > 2 or any(a in ['nuts', 'peanuts', 'shellfish'] for a in allergens):
                context_type = ContextType.ALLERGEN_SAFETY
            else:
                context_type = ContextType.DIETARY_PREFERENCE
                
            context_data = {
                'allergens': allergens,
                'dietary_preferences': dietary_preferences,
                'strict_mode': True
            }
            
        elif dietary_preferences:
            context_type = ContextType.DIETARY_PREFERENCE
            context_data = {
                'dietary_preferences': dietary_preferences,
                'strict_mode': False
            }
            
        else:
            # Check if regular customer
            visit_count = profile_data.get('visit_count', 0)
            if visit_count > 3:
                context_type = ContextType.REGULAR_CUSTOMER
                context_data = {
                    'favorites': profile_data.get('favorite_dishes', []),
                    'last_orders': profile_data.get('recent_orders', [])
                }
            else:
                context_type = ContextType.DEFAULT
                context_data = {}
        
        # Check for mixed restrictions
        if allergens and dietary_preferences:
            context_type = ContextType.MIXED_RESTRICTIONS
            
        return context_type, context_data
    
    @staticmethod
    def _check_context_override(message: str) -> Optional[Tuple[ContextType, Dict]]:
        """
        Check if the message contains a context override request
        """
        message_lower = message.lower()
        
        # Override to default context
        default_triggers = [
            "show me everything",
            "show all options",
            "i'm asking for someone else",
            "asking for a friend",
            "not for me",
            "i'm not allergic anymore",
            "ignore my restrictions",
            "full menu please"
        ]
        
        if any(trigger in message_lower for trigger in default_triggers):
            return ContextType.DEFAULT, {'override_reason': 'user_requested'}
        
        # Override to safety context
        safety_triggers = [
            "i'm allergic to",
            "i have an allergy",
            "severe allergy",
            "celiac disease",
            "anaphylactic"
        ]
        
        if any(trigger in message_lower for trigger in safety_triggers):
            return ContextType.ALLERGEN_SAFETY, {'override_reason': 'safety_detected'}
        
        return None
    
    @staticmethod
    def build_context_prompt(
        context_type: ContextType,
        context_data: Dict,
        business_name: str,
        base_prompt: str
    ) -> str:
        """
        Build the appropriate system prompt based on context type
        """
        
        if context_type == ContextType.ALLERGEN_SAFETY:
            return ContextManager._build_safety_prompt(context_data, business_name)
        
        elif context_type == ContextType.DIETARY_PREFERENCE:
            return ContextManager._build_preference_prompt(context_data, business_name)
            
        elif context_type == ContextType.REGULAR_CUSTOMER:
            return ContextManager._build_regular_customer_prompt(context_data, business_name)
            
        elif context_type == ContextType.MIXED_RESTRICTIONS:
            return ContextManager._build_mixed_restrictions_prompt(context_data, business_name)
            
        else:  # DEFAULT
            return base_prompt
    
    @staticmethod
    def _build_safety_prompt(context_data: Dict, business_name: str) -> str:
        """Build prompt for allergen safety context"""
        allergens = context_data.get('allergens', [])
        allergen_list = ', '.join(allergens)
        
        return f"""You are Maria, a safety-conscious server at {business_name}.

CRITICAL SAFETY MODE ACTIVE - Customer has severe allergies to: {allergen_list}

MANDATORY RULES:
1. ONLY recommend items that are 100% free from {allergen_list}
2. ALWAYS use filter_by_dietary([{allergen_list}]) before ANY recommendation
3. NEVER show or mention items containing these allergens
4. If customer asks about specific dish, use get_dish_details() to verify safety
5. Start responses with reassurance: "I'll make sure to only show you safe options..."

DEFAULT FILTERING:
- Your recommendations are PRE-FILTERED to exclude {allergen_list}
- Do not show unsafe items unless customer explicitly says "show me everything" or "asking for someone else"

If customer wants to see restricted items, ask: "I want to keep you safe. Are you sure you want to see items with {allergen_list}?"
"""
    
    @staticmethod
    def _build_preference_prompt(context_data: Dict, business_name: str) -> str:
        """Build prompt for dietary preference context"""
        preferences = context_data.get('dietary_preferences', [])
        pref_list = ', '.join(preferences)
        
        return f"""You are Maria, a thoughtful server at {business_name}.

Customer dietary preferences: {pref_list}

GUIDELINES:
1. Prioritize {pref_list} options in recommendations
2. Use filter_by_dietary([{pref_list}]) for initial suggestions
3. Mention that you're showing {pref_list} options
4. If limited options, you can say "I'm showing {pref_list} options first, but we have other items too"

Be flexible - if customer asks about non-{pref_list} items, help them happily.
"""
    
    @staticmethod
    def _build_regular_customer_prompt(context_data: Dict, business_name: str) -> str:
        """Build prompt for regular customer context"""
        favorites = context_data.get('favorites', [])
        
        prompt = f"""You are Maria, a friendly server at {business_name} who remembers regular customers.

This is a returning customer!
"""
        if favorites:
            prompt += f"Their favorite dishes: {', '.join(favorites[:3])}\n"
            prompt += "You can say things like 'Welcome back! Would you like your usual?' or 'I remember you enjoyed the...'"
        
        prompt += "\nBe warm and personal, but not overly familiar."
        
        return prompt
    
    @staticmethod
    def _build_mixed_restrictions_prompt(context_data: Dict, business_name: str) -> str:
        """Build prompt for mixed restrictions (most restrictive)"""
        allergens = context_data.get('allergens', [])
        preferences = context_data.get('dietary_preferences', [])
        
        all_restrictions = allergens + preferences
        restriction_list = ', '.join(all_restrictions)
        
        return f"""You are Maria, an extremely careful server at {business_name}.

MULTIPLE RESTRICTIONS ACTIVE: {restriction_list}
This includes both allergies ({', '.join(allergens)}) and preferences ({', '.join(preferences)})

EXTREME CAUTION REQUIRED:
1. MUST use filter_by_dietary([{restriction_list}]) for ALL recommendations
2. Default to the MOST restrictive interpretation
3. Very limited options - be honest about this
4. Always verify with tools before any claims

Start with: "I understand you need items that are {restriction_list}. Let me find suitable options..."
"""
    
    @staticmethod
    def should_update_context(
        current_context: ContextType,
        message: str,
        ai_response: str
    ) -> Optional[Dict]:
        """
        Check if we should update customer profile based on conversation
        
        Returns:
            Dict with updates needed, or None
        """
        message_lower = message.lower()
        
        updates = {}
        
        # Detect new allergens
        allergen_patterns = [
            "i'm allergic to",
            "i have an allergy to",
            "i can't eat",
            "i'm intolerant to"
        ]
        
        for pattern in allergen_patterns:
            if pattern in message_lower:
                # Extract what comes after
                # This is simplified - in production, use NLP
                words_after = message_lower.split(pattern)[1].split()
                if words_after:
                    potential_allergen = words_after[0].strip('.,!?')
                    updates['add_allergen'] = potential_allergen
        
        # Detect dietary preferences
        dietary_patterns = {
            "i'm vegan": "vegan",
            "i'm vegetarian": "vegetarian",
            "i don't eat meat": "vegetarian",
            "i keep halal": "halal",
            "i'm kosher": "kosher"
        }
        
        for pattern, preference in dietary_patterns.items():
            if pattern in message_lower:
                updates['add_dietary_preference'] = preference
        
        # Detect removal of restrictions
        if "i'm not allergic anymore" in message_lower:
            updates['clear_allergens'] = True
        
        if "i'm not vegan anymore" in message_lower:
            updates['remove_dietary_preference'] = 'vegan'
        
        return updates if updates else None