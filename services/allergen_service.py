"""
Allergen detection and dietary information service
"""
import re
from typing import List, Dict, Set, Optional
from sqlalchemy import text
from sqlalchemy.orm import Session
import logging

logger = logging.getLogger(__name__)

class AllergenService:
    """Service for detecting allergens and dietary restrictions"""
    
    # Common allergens and their variations
    ALLERGEN_KEYWORDS = {
        'nuts': [
            'nut', 'nuts', 'almond', 'cashew', 'pecan', 'walnut', 'pistachio', 
            'hazelnut', 'macadamia', 'pine nut', 'peanut', 'tree nut'
        ],
        'dairy': [
            'milk', 'cream', 'cheese', 'butter', 'yogurt', 'mozzarella', 'parmesan',
            'ricotta', 'gorgonzola', 'mascarpone', 'burrata', 'pecorino', 'romano',
            'dairy', 'lactose', 'whey', 'casein', 'ghee'
        ],
        'gluten': [
            'wheat', 'flour', 'bread', 'pasta', 'spaghetti', 'penne', 'linguine',
            'ravioli', 'gnocchi', 'lasagna', 'pizza', 'dough', 'crust', 'breadcrumbs',
            'baguette', 'croutons', 'gluten', 'barley', 'rye'
        ],
        'shellfish': [
            'shrimp', 'lobster', 'crab', 'scallop', 'oyster', 'mussel', 'clam',
            'crawfish', 'shellfish', 'crustacean', 'mollusk'
        ],
        'fish': [
            'fish', 'salmon', 'tuna', 'sea bass', 'cod', 'halibut', 'anchovy',
            'sardine', 'mackerel', 'trout'
        ],
        'eggs': [
            'egg', 'eggs', 'mayo', 'mayonnaise', 'aioli', 'carbonara', 'meringue',
            'custard', 'egg white', 'egg yolk'
        ],
        'soy': [
            'soy', 'soya', 'tofu', 'tempeh', 'edamame', 'miso', 'soy sauce'
        ],
        'sesame': [
            'sesame', 'tahini', 'sesame oil', 'sesame seed'
        ]
    }
    
    # Dietary restrictions
    DIETARY_KEYWORDS = {
        'vegetarian': {
            'exclude': ['meat', 'chicken', 'beef', 'pork', 'lamb', 'veal', 'duck', 
                       'bacon', 'prosciutto', 'guanciale', 'fish', 'seafood', 'shellfish'],
            'include': ['vegetarian', 'veggie', 'vegetable']
        },
        'vegan': {
            'exclude': ['meat', 'chicken', 'beef', 'pork', 'lamb', 'veal', 'duck',
                       'fish', 'seafood', 'dairy', 'cheese', 'milk', 'cream', 'butter',
                       'egg', 'honey', 'gelatin'],
            'include': ['vegan', 'plant-based']
        },
        'gluten-free': {
            'exclude': ['gluten', 'wheat', 'flour', 'bread', 'pasta', 'pizza'],
            'include': ['gluten-free', 'gf']
        },
        'pescatarian': {
            'exclude': ['meat', 'chicken', 'beef', 'pork', 'lamb', 'veal', 'duck'],
            'include': ['fish', 'seafood', 'pescatarian']
        }
    }
    
    def detect_allergens(self, ingredients: str, description: str = "") -> List[str]:
        """Detect allergens in ingredients and description"""
        allergens = []
        combined_text = f"{ingredients} {description}".lower()
        
        for allergen, keywords in self.ALLERGEN_KEYWORDS.items():
            if any(keyword in combined_text for keyword in keywords):
                allergens.append(allergen)
        
        return allergens
    
    def check_dietary_compliance(self, ingredients: str, description: str = "") -> Dict[str, bool]:
        """Check compliance with dietary restrictions"""
        combined_text = f"{ingredients} {description}".lower()
        compliance = {}
        
        for diet, rules in self.DIETARY_KEYWORDS.items():
            # Check exclusions
            has_excluded = any(item in combined_text for item in rules['exclude'])
            
            # For vegetarian/vegan, absence of excluded items means compliance
            if diet in ['vegetarian', 'vegan']:
                compliance[diet] = not has_excluded
            else:
                # For other diets, check inclusions or exclusions
                has_included = any(item in combined_text for item in rules.get('include', []))
                compliance[diet] = has_included or not has_excluded
        
        return compliance
    
    def get_items_for_dietary_need(self, db: Session, restaurant_id: str, 
                                  dietary_need: str) -> List[Dict]:
        """Get all menu items that meet a specific dietary need"""
        
        # Normalize dietary need
        need_lower = dietary_need.lower()
        
        # Handle different phrasings
        if 'nut' in need_lower and ('allerg' in need_lower or 'free' in need_lower):
            allergen_to_avoid = 'nuts'
        elif 'dairy' in need_lower and ('free' in need_lower or 'allerg' in need_lower):
            allergen_to_avoid = 'dairy'
        elif 'gluten' in need_lower and 'free' in need_lower:
            allergen_to_avoid = 'gluten'
        elif 'shellfish' in need_lower and ('allerg' in need_lower or 'free' in need_lower):
            allergen_to_avoid = 'shellfish'
        else:
            allergen_to_avoid = None
        
        # Get all menu items
        items = db.execute(text("""
            SELECT 
                item_name,
                item_price,
                item_category,
                item_ingredients,
                item_description,
                dietary_tags
            FROM menu_embeddings
            WHERE restaurant_id = :restaurant_id
        """), {'restaurant_id': restaurant_id}).fetchall()
        
        suitable_items = []
        
        for item in items:
            ingredients = item.item_ingredients or ''
            description = item.item_description or ''
            
            # Check allergen avoidance
            if allergen_to_avoid:
                allergens = self.detect_allergens(ingredients, description)
                if allergen_to_avoid in allergens:
                    continue  # Skip items with this allergen
            
            # Check dietary compliance
            if any(diet in need_lower for diet in ['vegetarian', 'vegan', 'pescatarian']):
                compliance = self.check_dietary_compliance(ingredients, description)
                
                if 'vegan' in need_lower and compliance.get('vegan'):
                    suitable_items.append(self._format_item(item))
                elif 'vegetarian' in need_lower and compliance.get('vegetarian'):
                    suitable_items.append(self._format_item(item))
                elif 'pescatarian' in need_lower and compliance.get('pescatarian'):
                    suitable_items.append(self._format_item(item))
            else:
                # If we're just avoiding an allergen, add items that don't have it
                if allergen_to_avoid:
                    suitable_items.append(self._format_item(item))
        
        return suitable_items
    
    def _format_item(self, item) -> Dict:
        """Format database item for response"""
        return {
            'name': item.item_name,
            'price': item.item_price,
            'category': item.item_category,
            'ingredients': item.item_ingredients,
            'description': item.item_description,
            'dietary_tags': item.dietary_tags
        }
    
    def get_allergen_info(self, db: Session, restaurant_id: str, 
                         item_name: str) -> Dict:
        """Get detailed allergen information for a specific item"""
        
        item = db.execute(text("""
            SELECT 
                item_name,
                item_ingredients,
                item_description
            FROM menu_embeddings
            WHERE restaurant_id = :restaurant_id
            AND LOWER(item_name) = LOWER(:item_name)
            LIMIT 1
        """), {
            'restaurant_id': restaurant_id,
            'item_name': item_name
        }).fetchone()
        
        if not item:
            return {'found': False}
        
        ingredients = item.item_ingredients or ''
        description = item.item_description or ''
        
        allergens = self.detect_allergens(ingredients, description)
        dietary = self.check_dietary_compliance(ingredients, description)
        
        return {
            'found': True,
            'name': item.item_name,
            'allergens': allergens,
            'dietary_compliance': dietary,
            'ingredients': ingredients
        }
    
    def format_allergen_warning(self, allergens: List[str]) -> str:
        """Format allergen information for customer display"""
        if not allergens:
            return ""
        
        if len(allergens) == 1:
            return f"⚠️ Contains {allergens[0]}"
        else:
            return f"⚠️ Contains: {', '.join(allergens)}"

# Singleton instance
allergen_service = AllergenService()