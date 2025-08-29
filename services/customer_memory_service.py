"""
Customer Memory Service - Extract and store customer information
"""
import re
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models.customer_profile import CustomerProfile
import logging

logger = logging.getLogger(__name__)

class CustomerMemoryService:
    """Extract and manage customer information from conversations"""
    
    @staticmethod
    def extract_customer_info(message: str, current_profile: Optional[CustomerProfile] = None) -> Dict:
        """Extract customer information from message"""
        info = {}
        message_lower = message.lower()
        
        # Extract name
        name_patterns = [
            r"my name is (\w+)",
            r"i'm (\w+)",
            r"i am (\w+)",
            r"call me (\w+)",
            r"this is (\w+)"
        ]
        for pattern in name_patterns:
            match = re.search(pattern, message_lower)
            if match:
                info['name'] = match.group(1).capitalize()
                break
        
        # Extract dietary restrictions
        if any(word in message_lower for word in ['vegetarian', 'vegan', 'halal', 'kosher']):
            restrictions = []
            if 'vegetarian' in message_lower:
                restrictions.append('vegetarian')
            if 'vegan' in message_lower:
                restrictions.append('vegan')
            if 'halal' in message_lower:
                restrictions.append('halal')
            if 'kosher' in message_lower:
                restrictions.append('kosher')
            info['dietary_restrictions'] = restrictions
        
        # Extract allergies
        allergy_keywords = ['allergic', 'allergy', "can't have", "cannot have"]
        if any(keyword in message_lower for keyword in allergy_keywords):
            allergies = []
            common_allergens = ['nuts', 'peanuts', 'shellfish', 'dairy', 'milk', 'eggs', 'gluten', 'soy']
            for allergen in common_allergens:
                if allergen in message_lower:
                    allergies.append(allergen)
            if allergies:
                info['allergies'] = allergies
        
        # Extract preferences
        if 'spicy' in message_lower or 'spice' in message_lower:
            if 'not spicy' in message_lower or 'no spice' in message_lower:
                info['spice_preference'] = 'mild'
            elif 'extra spicy' in message_lower:
                info['spice_preference'] = 'extra hot'
            elif 'very spicy' in message_lower:
                info['spice_preference'] = 'hot'
        
        return info
    
    @staticmethod
    def update_customer_profile(db: Session, client_id: str, restaurant_id: str, extracted_info: Dict) -> CustomerProfile:
        """Update or create customer profile with extracted information"""
        
        # Get or create profile
        profile = db.query(CustomerProfile).filter(
            CustomerProfile.client_id == client_id,
            CustomerProfile.restaurant_id == restaurant_id
        ).first()
        
        if not profile:
            profile = CustomerProfile(
                client_id=client_id,
                restaurant_id=restaurant_id
            )
            db.add(profile)
        
        # Update with extracted info
        if 'name' in extracted_info and not profile.name:
            profile.name = extracted_info['name']
            logger.info(f"Updated customer name: {profile.name}")
        
        if 'dietary_restrictions' in extracted_info:
            # Merge with existing
            existing = set(profile.dietary_restrictions or [])
            existing.update(extracted_info['dietary_restrictions'])
            profile.dietary_restrictions = list(existing)
            logger.info(f"Updated dietary restrictions: {profile.dietary_restrictions}")
        
        if 'allergies' in extracted_info:
            # Merge with existing
            existing = set(profile.allergies or [])
            existing.update(extracted_info['allergies'])
            profile.allergies = list(existing)
            logger.info(f"Updated allergies: {profile.allergies}")
        
        if 'spice_preference' in extracted_info:
            profile.spice_preference = extracted_info['spice_preference']
        
        db.commit()
        return profile
    
    @staticmethod
    def get_customer_context(profile: Optional[CustomerProfile]) -> str:
        """Generate context string for AI about customer"""
        if not profile:
            return ""
        
        context_parts = []
        
        if profile.name:
            context_parts.append(f"Customer's name is {profile.name}")
        
        if profile.dietary_restrictions:
            context_parts.append(f"Dietary restrictions: {', '.join(profile.dietary_restrictions)}")
        
        if profile.allergies:
            context_parts.append(f"Allergies: {', '.join(profile.allergies)}")
        
        if profile.spice_preference and profile.spice_preference != 'medium':
            context_parts.append(f"Spice preference: {profile.spice_preference}")
        
        if profile.favorite_dishes:
            context_parts.append(f"Favorite dishes: {', '.join(profile.favorite_dishes[:3])}")
        
        if profile.order_count > 0:
            context_parts.append(f"Regular customer ({profile.order_count} orders)")
        
        return "\n".join(context_parts) if context_parts else ""