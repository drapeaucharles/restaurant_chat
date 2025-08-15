"""
Fix for language consistency - Force English responses
"""

def detect_language_fixed(text: str) -> str:
    """
    Improved language detection that defaults to English unless 
    explicitly requested in another language
    """
    text_lower = text.lower()
    
    # Explicit language requests
    explicit_spanish = any(phrase in text_lower for phrase in [
        'en español', 'in spanish', 'habla español', 'spanish please'
    ])
    explicit_french = any(phrase in text_lower for phrase in [
        'en français', 'in french', 'parlez français', 'french please'
    ])
    explicit_portuguese = any(phrase in text_lower for phrase in [
        'em português', 'in portuguese', 'fala português', 'portuguese please'
    ])
    
    if explicit_spanish:
        return "es"
    elif explicit_french:
        return "fr"
    elif explicit_portuguese:
        return "pt"
    
    # Check for strong language indicators (multiple words in sentence)
    spanish_words = ['hola', 'buenas', 'quiero', 'tiene', 'gracias', 'por favor', 'comida', 'platos']
    french_words = ['bonjour', 'bonsoir', 'je', 'voudrais', 'avez-vous', 'merci', 'plats', 'menu']
    portuguese_words = ['olá', 'boa', 'quero', 'tem', 'obrigado', 'por favor', 'comida', 'pratos']
    
    spanish_count = sum(1 for word in spanish_words if word in text_lower)
    french_count = sum(1 for word in french_words if word in text_lower)
    portuguese_count = sum(1 for word in portuguese_words if word in text_lower)
    
    # Require at least 3 matching words to switch language
    if spanish_count >= 3:
        return "es"
    elif french_count >= 3:
        return "fr"
    elif portuguese_count >= 3:
        return "pt"
    else:
        # Default to English
        return "en"

def force_english_unless_requested(original_detect_func):
    """
    Decorator to force English responses unless explicitly requested
    """
    def wrapper(text: str) -> str:
        # Always return English for now until we fix the Portuguese issue
        return "en"
    return wrapper

# Export the fixed function
detect_language = detect_language_fixed