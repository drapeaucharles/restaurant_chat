"""
Universal response validation service to ensure AI doesn't hallucinate products/services
Works for restaurants, legal services, hotels, etc.
"""
import re
import logging
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class UniversalResponseValidator:
    """Validates AI responses against actual business data"""
    
    def __init__(self):
        self.price_pattern = re.compile(r'\$\d+(?:,\d{3})*(?:\.\d{2})?')  # Handles $1,500.00
        self.item_pattern = re.compile(r'[-•]\s*([^(\n]+?)(?:\s*\(|$|:)')
        
    def extract_mentioned_items(self, response: str, business_type: str = "restaurant") -> List[Dict[str, str]]:
        """Extract product/service names and prices mentioned in response"""
        items = []
        lines = response.split('\n')
        
        for line in lines:
            # Look for bullet points or dashes with items
            if any(marker in line for marker in ['•', '-', '·']):
                # Extract item name - more flexible pattern
                item_match = self.item_pattern.search(line)
                if not item_match:
                    # Try alternative pattern for numbered lists
                    alt_pattern = re.compile(r'^\d+\.\s*([^(\n]+?)(?:\s*\(|$|:)')
                    item_match = alt_pattern.search(line)
                
                if item_match:
                    item_name = item_match.group(1).strip()
                    
                    # Clean up the name
                    item_name = item_name.rstrip('.,;:')
                    
                    # Extract price
                    price_match = self.price_pattern.search(line)
                    price = price_match.group(0) if price_match else None
                    
                    # Extract duration for services
                    duration = None
                    if business_type in ["legal_visa", "consulting", "service"]:
                        duration_pattern = re.compile(r'(\d+-?\d*\s*(?:days?|weeks?|months?|hours?))')
                        duration_match = duration_pattern.search(line)
                        duration = duration_match.group(0) if duration_match else None
                    
                    items.append({
                        'name': item_name,
                        'price': price,
                        'duration': duration,
                        'line': line
                    })
        
        return items
    
    def get_actual_products(self, db: Session, business_id: str) -> Dict[str, Dict]:
        """Get all actual products/services from database"""
        # First, get business type
        business_query = text("""
            SELECT business_type FROM businesses 
            WHERE business_id = :business_id
        """)
        result = db.execute(business_query, {"business_id": business_id}).fetchone()
        business_type = result[0] if result and result[0] else "restaurant"
        
        # Get products
        query = text("""
            SELECT id, name, price, category, description, 
                   product_type, duration
            FROM products
            WHERE business_id = :business_id
            AND available = true
        """)
        
        results = db.execute(query, {"business_id": business_id}).fetchall()
        
        products = {}
        for row in results:
            # Create multiple lookup keys for flexible matching
            name = row[1]
            name_lower = name.lower()
            
            product_data = {
                'id': row[0],
                'name': name,
                'price': row[2],
                'category': row[3],
                'description': row[4],
                'product_type': row[5],
                'duration': row[6],
                'business_type': business_type
            }
            
            # Add with multiple keys for better matching
            products[name_lower] = product_data
            
            # Also add without common words for better matching
            simplified_name = name_lower
            for word in ['the', 'a', 'an', 'and', 'or', 'with']:
                simplified_name = simplified_name.replace(f' {word} ', ' ')
            if simplified_name != name_lower:
                products[simplified_name] = product_data
            
            # For services, also match by service ID
            if row[5] in ['service', 'consultation']:
                service_key = row[0].replace(f"{business_id}_", "")
                products[service_key.lower()] = product_data
        
        return products
    
    def find_best_match(self, item_name: str, products: Dict[str, Dict]) -> Optional[Dict]:
        """Find best matching product allowing for slight variations"""
        item_lower = item_name.lower().strip()
        
        # Direct match
        if item_lower in products:
            return products[item_lower]
        
        # Try without common words
        simplified = item_lower
        for word in ['the', 'a', 'an', 'and', 'or', 'with']:
            simplified = simplified.replace(f' {word} ', ' ')
        if simplified in products:
            return products[simplified]
        
        # Partial match - product name contains the searched term
        for key, product in products.items():
            if item_lower in key or key in item_lower:
                return product
        
        # Very flexible match - any word overlap
        item_words = set(item_lower.split())
        for key, product in products.items():
            key_words = set(key.split())
            if len(item_words & key_words) >= min(2, len(item_words)):
                return product
        
        return None
    
    def validate_and_correct(self, response: str, db: Session, business_id: str) -> str:
        """Validate response and correct any inaccuracies"""
        try:
            # Get actual products
            actual_products = self.get_actual_products(db, business_id)
            if not actual_products:
                return response
            
            # Determine business type from products
            business_type = next(iter(actual_products.values())).get('business_type', 'restaurant')
            
            # Extract mentioned items
            mentioned_items = self.extract_mentioned_items(response, business_type)
            
            corrected_response = response
            corrections_made = 0
            
            for item in mentioned_items:
                # Find matching product
                match = self.find_best_match(item['name'], actual_products)
                
                if match:
                    # Check if price needs correction
                    if item['price']:
                        mentioned_price = float(item['price'].replace('$', '').replace(',', ''))
                        actual_price = float(match['price'])
                        
                        # Allow 10% tolerance for price variations
                        if abs(mentioned_price - actual_price) > actual_price * 0.1:
                            # Format price based on business type
                            if business_type in ["legal_visa", "consulting"] and actual_price >= 1000:
                                formatted_price = f"${actual_price:,.0f}"
                            else:
                                formatted_price = f"${actual_price:.2f}"
                            
                            # Replace the incorrect price
                            old_price = item['price']
                            new_line = item['line'].replace(old_price, formatted_price)
                            corrected_response = corrected_response.replace(item['line'], new_line)
                            corrections_made += 1
                            logger.info(f"Corrected price for {item['name']}: {old_price} → {formatted_price}")
                    
                    # Check if the name needs slight correction
                    if item['name'].lower() != match['name'].lower():
                        # Only correct if it's significantly different
                        if item['name'].lower().replace(' ', '') != match['name'].lower().replace(' ', ''):
                            corrected_response = corrected_response.replace(item['name'], match['name'])
                            corrections_made += 1
                            logger.info(f"Corrected name: {item['name']} → {match['name']}")
                else:
                    # Item not found - this might be a hallucination
                    logger.warning(f"Could not find product/service: {item['name']}")
                    # For now, we'll leave it as the AI might be referring to something generic
            
            if corrections_made > 0:
                logger.info(f"Made {corrections_made} corrections to the response")
            
            return corrected_response
            
        except Exception as e:
            logger.error(f"Error validating response: {e}")
            return response
    
    # Backward compatibility methods
    def get_actual_menu_items(self, db: Session, restaurant_id: str) -> Dict[str, Dict]:
        """Backward compatibility for restaurant systems"""
        return self.get_actual_products(db, restaurant_id)

# Create singleton instance
universal_response_validator = UniversalResponseValidator()

# Backward compatibility
response_validator = universal_response_validator  # Alias for existing code