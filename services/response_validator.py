"""
Response validation service to ensure AI doesn't hallucinate menu items
"""
import re
import logging
from typing import List, Dict, Set, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

logger = logging.getLogger(__name__)

class ResponseValidator:
    """Validates AI responses against actual menu data"""
    
    def __init__(self):
        self.price_pattern = re.compile(r'\$\d+(?:\.\d{2})?')
        self.item_pattern = re.compile(r'•\s*([^(\n]+?)(?:\s*\(|$)')
        
    def extract_mentioned_items(self, response: str) -> List[Dict[str, str]]:
        """Extract item names and prices mentioned in response"""
        items = []
        lines = response.split('\n')
        
        for line in lines:
            # Look for bullet points with items
            if '•' in line:
                # Extract item name
                item_match = self.item_pattern.search(line)
                if item_match:
                    item_name = item_match.group(1).strip()
                    
                    # Extract price
                    price_match = self.price_pattern.search(line)
                    price = price_match.group(0) if price_match else None
                    
                    items.append({
                        'name': item_name,
                        'price': price,
                        'line': line
                    })
        
        return items
    
    def get_actual_menu_items(self, db: Session, restaurant_id: str) -> Dict[str, Dict]:
        """Get all actual menu items from database"""
        results = db.execute(text("""
            SELECT item_name, item_price, item_category, item_description
            FROM menu_embeddings
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id}).fetchall()
        
        # Create lookup dict by normalized name
        menu_items = {}
        for item in results:
            normalized_name = self.normalize_item_name(item.item_name)
            menu_items[normalized_name] = {
                'name': item.item_name,
                'price': item.item_price,
                'category': item.item_category,
                'description': item.item_description
            }
        
        return menu_items
    
    def normalize_item_name(self, name: str) -> str:
        """Normalize item name for comparison"""
        # Remove common variations
        normalized = name.lower().strip()
        normalized = re.sub(r'\s+', ' ', normalized)  # Multiple spaces to single
        normalized = re.sub(r'[^\w\s]', '', normalized)  # Remove punctuation
        return normalized
    
    def validate_response(self, db: Session, restaurant_id: str, response: str) -> Dict:
        """Validate response against actual menu"""
        
        # Extract mentioned items
        mentioned_items = self.extract_mentioned_items(response)
        
        # Get actual menu
        actual_menu = self.get_actual_menu_items(db, restaurant_id)
        
        # Check each mentioned item
        validation_results = {
            'valid': True,
            'hallucinated_items': [],
            'corrections': {},
            'warnings': []
        }
        
        for item in mentioned_items:
            normalized_mentioned = self.normalize_item_name(item['name'])
            
            # Check if item exists
            found = False
            for normalized_actual, actual_data in actual_menu.items():
                if normalized_mentioned in normalized_actual or normalized_actual in normalized_mentioned:
                    found = True
                    
                    # Check price accuracy
                    if item['price'] and actual_data['price'] != item['price']:
                        validation_results['warnings'].append(
                            f"Price mismatch for {item['name']}: mentioned {item['price']} vs actual {actual_data['price']}"
                        )
                        validation_results['corrections'][item['name']] = actual_data
                    break
            
            if not found:
                validation_results['valid'] = False
                validation_results['hallucinated_items'].append(item['name'])
                
                # Try to find similar items
                similar = self.find_similar_items(normalized_mentioned, actual_menu)
                if similar:
                    validation_results['corrections'][item['name']] = similar[0]
        
        return validation_results
    
    def find_similar_items(self, item_name: str, menu_items: Dict[str, Dict]) -> List[Dict]:
        """Find items with similar names"""
        similar = []
        item_words = set(item_name.split())
        
        for normalized, data in menu_items.items():
            menu_words = set(normalized.split())
            common_words = item_words.intersection(menu_words)
            
            # If they share significant words
            if len(common_words) >= len(item_words) * 0.5:
                similar.append(data)
        
        return similar
    
    def create_validated_context(self, db: Session, restaurant_id: str, 
                               relevant_items: List[Dict]) -> str:
        """Create context with only validated items"""
        
        # Get actual menu for validation
        actual_menu = self.get_actual_menu_items(db, restaurant_id)
        
        # Build validated context
        validated_items = []
        for item in relevant_items:
            normalized = self.normalize_item_name(item['name'])
            
            # Find in actual menu
            for norm_actual, actual_data in actual_menu.items():
                if normalized in norm_actual or norm_actual in normalized:
                    # Use actual data to prevent hallucination
                    validated_items.append({
                        'name': actual_data['name'],
                        'price': actual_data['price'],
                        'category': actual_data.get('category'),
                        'description': actual_data.get('description')
                    })
                    break
        
        # Build context string
        context = "\nMenu items (ONLY mention these):\n"
        for item in validated_items:
            context += f"• {item['name']} ({item['price']})"
            if item.get('description'):
                desc = item['description'][:50] + "..." if len(item['description']) > 50 else item['description']
                context += f" - {desc}"
            context += "\n"
        
        context += "\n⚠️ IMPORTANT: Only mention items listed above. Do NOT invent or guess other items."
        
        return context

# Singleton instance
response_validator = ResponseValidator()