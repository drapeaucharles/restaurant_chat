# services/intent_classifier.py

from typing import Tuple, List
import re

class IntentClassifier:
    """
    Lightweight intent classifier to determine query type and complexity.
    This helps route queries to the appropriate processing level.
    """
    
    # Keywords for different intent types
    FILTER_KEYWORDS = [
        "show me only", "filter", "just show", "only show", "display only",
        "list only", "show just", "find me only", "search for only"
    ]
    
    INFO_KEYWORDS = [
        "what is", "what are", "tell me about", "explain", "describe",
        "how does", "how do", "when is", "when are", "where is",
        "who is", "why is", "why do", "does it have", "is it", "are there"
    ]
    
    PREFERENCE_KEYWORDS = [
        "don't like", "hate", "avoid", "allergic", "intolerant", "can't eat",
        "no ", "without", "free from", "love", "prefer", "favorite", "like",
        "want", "looking for", "craving", "mood for"
    ]
    
    SIMPLE_QUERIES = [
        "menu", "hours", "location", "contact", "delivery", "takeout",
        "parking", "wifi", "reservations", "specials", "price", "cost"
    ]
    
    COMPLEX_INDICATORS = [
        "and", "or", "but", "except", "besides", "also", "with", "without",
        "between", "under", "over", "less than", "more than"
    ]
    
    @classmethod
    def classify_intent(cls, query: str) -> Tuple[str, bool, List[str]]:
        """
        Classify the intent of a query.
        
        Returns:
            Tuple of (intent_type, is_complex, detected_features)
            - intent_type: 'filter', 'info', 'preference', 'simple', 'general'
            - is_complex: True if query requires full processing
            - detected_features: List of detected features for context
        """
        query_lower = query.lower().strip()
        detected_features = []
        
        # Check for filter intent (highest priority)
        for keyword in cls.FILTER_KEYWORDS:
            if keyword in query_lower:
                detected_features.append('filter_request')
                return ('filter', True, detected_features)
        
        # Check for simple queries (can use cache/simple response)
        normalized = query_lower.rstrip('?').rstrip('.').strip()
        if normalized in cls.SIMPLE_QUERIES or len(normalized.split()) <= 2:
            detected_features.append('simple_query')
            return ('simple', False, detected_features)
        
        # Check for preference expressions
        preference_score = 0
        for keyword in cls.PREFERENCE_KEYWORDS:
            if keyword in query_lower:
                preference_score += 1
                detected_features.append(f'preference:{keyword.strip()}')
        
        if preference_score > 0:
            is_complex = preference_score > 1 or any(ind in query_lower for ind in cls.COMPLEX_INDICATORS)
            return ('preference', is_complex, detected_features)
        
        # Check for informational queries
        for keyword in cls.INFO_KEYWORDS:
            if keyword in query_lower:
                detected_features.append('info_request')
                # Info queries are generally not complex unless they have multiple parts
                is_complex = any(ind in query_lower for ind in cls.COMPLEX_INDICATORS)
                return ('info', is_complex, detected_features)
        
        # Check complexity for general queries
        is_complex = (
            len(query_lower.split()) > 10 or
            any(ind in query_lower for ind in cls.COMPLEX_INDICATORS) or
            query_lower.count('?') > 1
        )
        
        return ('general', is_complex, detected_features)
    
    @classmethod
    def needs_full_menu_context(cls, intent_type: str, query: str) -> bool:
        """
        Determine if the query needs full menu context or can work with partial data.
        """
        if intent_type == 'filter':
            return True  # Need all items for show/hide operations
        
        if intent_type == 'simple':
            return False  # Simple queries don't need menu context
        
        # Check if query mentions specific food items or categories
        food_indicators = [
            "dish", "food", "meal", "menu", "item", "option",
            "pasta", "pizza", "salad", "soup", "dessert", "appetizer",
            "drink", "beverage", "wine", "beer", "cocktail"
        ]
        
        query_lower = query.lower()
        mentions_food = any(indicator in query_lower for indicator in food_indicators)
        
        return mentions_food
    
    @classmethod
    def get_model_recommendation(cls, intent_type: str, is_complex: bool) -> str:
        """
        Recommend which model to use based on intent and complexity.
        """
        # Use GPT-3.5 for simple queries and basic info requests
        if intent_type in ['simple', 'info'] and not is_complex:
            return 'gpt-3.5-turbo'
        
        # Use GPT-4 for complex queries, filters, and preference handling
        return 'gpt-4'