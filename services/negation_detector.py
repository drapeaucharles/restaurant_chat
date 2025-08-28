"""
Advanced negation detection for food preferences
"""
import re
from typing import Tuple, List

class NegationDetector:
    """Detects negation patterns in food preference queries"""
    
    # Negation patterns with word boundaries
    NEGATION_PATTERNS = [
        r'\bno\s+(\w+)',           # "no eggs", "no nuts"
        r'\bnot\s+(\w+)',          # "not eggs"
        r'\bwithout\s+(\w+)',      # "without eggs"
        r'\bdon\'?t\s+(?:like|want|eat)\s+(\w+)',  # "don't like eggs"
        r'\bcan\'?t\s+(?:have|eat)\s+(\w+)',       # "can't have eggs"
        r'\bavoid(?:ing)?\s+(\w+)', # "avoid eggs", "avoiding eggs"
        r'\ballergic\s+(?:to\s+)?(\w+)',  # "allergic to eggs"
        r'\bdislike\s+(\w+)',      # "dislike eggs"
        r'\bhate\s+(\w+)',         # "hate eggs"
        r'\bfree\s+(?:from|of)\s+(\w+)',  # "free from eggs"
        r'\b(\w+)\s*-?\s*free',    # "egg-free", "egg free"
        r'\bexcept\s+(\w+)',       # "except eggs"
        r'\bbut\s+not\s+(\w+)',    # "but not eggs"
        r'\banything\s+but\s+(\w+)', # "anything but eggs"
        r'\bnot\s+a\s+fan\s+of\s+(\w+)', # "not a fan of eggs"
        r'\bstay\s+away\s+from\s+(\w+)', # "stay away from eggs"
    ]
    
    # False positive patterns to check
    FALSE_POSITIVE_PATTERNS = [
        r'\bknow?\s+',             # "I know eggs..."
        r'\bnot\s+sure',           # "not sure if..."
        r'\bno\s+problem',         # "no problem with eggs"
        r'\bno\s+issue',           # "no issue with eggs"
    ]
    
    # Double negative patterns
    DOUBLE_NEGATIVE_PATTERNS = [
        r'don\'?t\s+(?:like|want)\s+.*\s+without',  # "don't like pizza without cheese"
        r'not\s+.*\s+unless',      # "not good unless it has eggs"
        r'no\s+.*\s+without',      # "no pasta without cheese"
    ]
    
    @classmethod
    def detect_negation(cls, query: str) -> Tuple[bool, List[str]]:
        """
        Detect if query contains negation and extract negated items
        
        Returns:
            Tuple of (is_negative, list_of_negated_ingredients)
        """
        query_lower = query.lower()
        negated_items = []
        
        # Check for false positives first
        for pattern in cls.FALSE_POSITIVE_PATTERNS:
            if re.search(pattern, query_lower):
                # Might be a false positive, need more careful analysis
                pass
        
        # Check for double negatives
        for pattern in cls.DOUBLE_NEGATIVE_PATTERNS:
            if re.search(pattern, query_lower):
                # This is actually a positive preference!
                return False, []
        
        # Check negation patterns
        for pattern in cls.NEGATION_PATTERNS:
            matches = re.findall(pattern, query_lower)
            if matches:
                # Extract the negated items
                for match in matches:
                    if isinstance(match, str) and len(match) > 2:
                        # Clean up the match
                        item = match.strip().rstrip('s')  # Remove plural
                        if item and item not in ['the', 'any', 'all', 'some']:
                            negated_items.append(item)
        
        return len(negated_items) > 0, negated_items
    
    @classmethod
    def extract_preferences(cls, query: str) -> dict:
        """
        Extract both positive and negative preferences from query
        
        Returns dict with 'likes' and 'dislikes' lists
        """
        query_lower = query.lower()
        is_negative, negated_items = cls.detect_negation(query)
        
        preferences = {
            'dislikes': negated_items,
            'likes': []
        }
        
        # Positive patterns
        positive_patterns = [
            r'\blove\s+(\w+)',
            r'\blike\s+(\w+)',
            r'\bwant\s+(\w+)',
            r'\bprefer\s+(\w+)',
            r'\bfan\s+of\s+(\w+)',
            r'\bcraving\s+(\w+)',
            r'\blooking\s+for\s+(\w+)',
        ]
        
        # Only extract positive if no negation detected
        if not is_negative:
            for pattern in positive_patterns:
                matches = re.findall(pattern, query_lower)
                for match in matches:
                    if isinstance(match, str) and len(match) > 2:
                        item = match.strip().rstrip('s')
                        if item and item not in ['the', 'any', 'all', 'some']:
                            preferences['likes'].append(item)
        
        return preferences
    
    @classmethod
    def is_dietary_restriction(cls, query: str) -> bool:
        """Check if this is a dietary restriction rather than just preference"""
        restriction_keywords = [
            'allergic', 'allergy', 'intolerant', 'intolerance',
            'can\'t have', 'cannot have', 'makes me sick',
            'dietary restriction', 'medical', 'condition'
        ]
        
        query_lower = query.lower()
        return any(keyword in query_lower for keyword in restriction_keywords)


# Test cases
if __name__ == "__main__":
    test_queries = [
        "I don't like eggs",
        "no eggs please",
        "I love eggs",
        "anything but eggs",
        "I'm allergic to eggs",
        "egg-free options",
        "I want gluten free",
        "I know eggs are healthy",
        "not sure about eggs",
        "I don't like pizza without cheese",
        "stay away from nuts",
        "not a fan of mushrooms",
        "I hate spicy food",
    ]
    
    detector = NegationDetector()
    for query in test_queries:
        is_neg, items = detector.detect_negation(query)
        prefs = detector.extract_preferences(query)
        is_restriction = detector.is_dietary_restriction(query)
        print(f"\nQuery: '{query}'")
        print(f"  Negative: {is_neg}, Items: {items}")
        print(f"  Preferences: {prefs}")
        print(f"  Dietary restriction: {is_restriction}")