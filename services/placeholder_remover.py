"""
Placeholder Remover Service
Ensures AI responses never contain placeholder text
"""
import re
import logging

logger = logging.getLogger(__name__)

class PlaceholderRemover:
    """Remove any placeholder text from AI responses"""
    
    # Common placeholder patterns
    PLACEHOLDER_PATTERNS = [
        r'\[Customer\'s Name\]',
        r'\[Customer Name\]',
        r'\[Your Name\]',
        r'\[Business Name\]',
        r'\[Restaurant Name\]',
        r'\[Company Name\]',
        r'\[.*?\]',  # Any text in brackets
        r'\{Customer\'s Name\}',
        r'\{Customer Name\}',
        r'\{Your Name\}',
        r'\{.*?\}',  # Any text in curly braces
        r'<Customer\'s Name>',
        r'<Customer Name>',
        r'<Your Name>',
        r'<.*?>',  # Any text in angle brackets
    ]
    
    # Replacement mappings
    REPLACEMENTS = {
        'Hello [Customer\'s Name]': 'Hello',
        'Hi [Customer\'s Name]': 'Hi there',
        'Dear [Customer\'s Name]': 'Hello',
        'Welcome [Customer\'s Name]': 'Welcome',
        '[Customer\'s Name]': '',
        '[Your Name]': '',
        '[Business Name]': '',
        'I\'m [Your Name]': 'I\'m here to help',
        'My name is [Your Name]': 'I\'m here to assist you',
    }
    
    def remove_placeholders(self, text: str) -> str:
        """Remove all placeholder text from response"""
        if not text:
            return text
            
        original_text = text
        
        # First, try specific replacements
        for placeholder, replacement in self.REPLACEMENTS.items():
            text = text.replace(placeholder, replacement)
        
        # Then, remove any remaining placeholders using patterns
        for pattern in self.PLACEHOLDER_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # Clean up multiple spaces and punctuation issues
        text = re.sub(r'\s+', ' ', text)  # Multiple spaces to single
        text = re.sub(r'\s+([,.!?])', r'\1', text)  # Remove space before punctuation
        text = re.sub(r'^[,.\s]+', '', text)  # Remove leading punctuation
        text = re.sub(r'^\s*Hi\s*,', 'Hi there,', text)  # Fix "Hi ," to "Hi there,"
        text = re.sub(r'^\s*Hello\s*,', 'Hello!', text)  # Fix "Hello ," to "Hello!"
        
        # Ensure proper sentence start
        text = text.strip()
        if text and not text[0].isupper():
            text = text[0].upper() + text[1:]
        
        # Log if we made changes
        if text != original_text:
            logger.warning(f"Removed placeholders from response. Original: '{original_text[:100]}...'")
        
        return text
    
    def validate_response(self, text: str) -> bool:
        """Check if response contains placeholders"""
        if not text:
            return True
            
        # Check for any bracket patterns
        bracket_patterns = [r'\[.*?\]', r'\{.*?\}', r'<.*?>']
        for pattern in bracket_patterns:
            if re.search(pattern, text):
                return False
        
        # Check for specific placeholder text
        placeholder_keywords = [
            "Customer's Name",
            "Customer Name",
            "Your Name",
            "Business Name",
        ]
        for keyword in placeholder_keywords:
            if keyword in text:
                return False
        
        return True
    
    def clean_response(self, text: str, customer_name: str = None) -> str:
        """Clean response and optionally inject actual customer name"""
        # First remove all placeholders
        text = self.remove_placeholders(text)
        
        # If we have a customer name and the text starts with a generic greeting, personalize it
        if customer_name and text.startswith(('Hello!', 'Hi there', 'Hi!', 'Hello')):
            # Replace generic greeting with personalized one
            if text.startswith('Hello!'):
                text = f"Hello {customer_name}!" + text[6:]
            elif text.startswith('Hi there'):
                text = f"Hi {customer_name}" + text[8:]
            elif text.startswith('Hi!'):
                text = f"Hi {customer_name}!" + text[3:]
            elif text.startswith('Hello'):
                text = f"Hello {customer_name}" + text[5:]
        
        return text

# Singleton instance
placeholder_remover = PlaceholderRemover()