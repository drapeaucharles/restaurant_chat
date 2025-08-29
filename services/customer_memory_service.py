"""
Customer Memory Service - Extract and store customer information
"""
import re
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
import models
import logging

logger = logging.getLogger(__name__)

class CustomerMemoryService:
    """Extract and manage customer information from conversations"""
    
    @staticmethod
    def extract_customer_info(message: str, current_profile: Optional[models.CustomerProfile] = None) -> Dict:
        """Extract customer information from message"""
        info = {}
        message_lower = message.lower()
        
        # Check for correction/update patterns
        is_correction = any(phrase in message_lower for phrase in [
            "i'm not", "i am not", "actually", "correction", "update", 
            "not allergic", "no longer", "changed", "mistake"
        ])
        
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
        
        # Extract allergies (with removal support)
        allergy_keywords = ['allergic', 'allergy', "can't have", "cannot have"]
        negative_keywords = ['not allergic', 'no allergy', 'not have allergy']
        
        # Check for allergy removal
        if any(keyword in message_lower for keyword in negative_keywords):
            removed_allergies = []
            common_allergens = ['nuts', 'peanuts', 'shellfish', 'dairy', 'milk', 'eggs', 'gluten', 'soy']
            for allergen in common_allergens:
                if allergen in message_lower:
                    removed_allergies.append(allergen)
            if removed_allergies:
                info['remove_allergies'] = removed_allergies
        # Check for allergy addition
        elif any(keyword in message_lower for keyword in allergy_keywords):
            allergies = []
            common_allergens = ['nuts', 'peanuts', 'shellfish', 'dairy', 'milk', 'eggs', 'gluten', 'soy']
            for allergen in common_allergens:
                if allergen in message_lower:
                    allergies.append(allergen)
            if allergies:
                info['allergies'] = allergies
        
        # Extract preferences
        if 'spicy' in message_lower or 'spice' in message_lower:
            if 'not spicy' in message_lower or 'no spice' in message_lower or "don't like spicy" in message_lower:
                info['spice_preference'] = 'mild'
            elif 'extra spicy' in message_lower or 'really spicy' in message_lower:
                info['spice_preference'] = 'extra_spicy'
            elif 'very spicy' in message_lower:
                info['spice_preference'] = 'hot'
            elif 'love spicy' in message_lower or 'like spicy' in message_lower:
                info['spice_preference'] = 'hot'
        
        # Extract general preferences
        preferences_update = {}
        if "i love" in message_lower or "i like" in message_lower:
            # Extract what they love/like
            match = re.search(r"i (?:love|like) ([^,.!?]+)", message_lower)
            if match:
                item = match.group(1).strip()
                preferences_update[f'likes_{item.replace(" ", "_")}'] = True
        
        if "i don't like" in message_lower or "i hate" in message_lower:
            # Extract what they don't like
            match = re.search(r"i (?:don't like|hate) ([^,.!?]+)", message_lower)
            if match:
                item = match.group(1).strip()
                preferences_update[f'dislikes_{item.replace(" ", "_")}'] = True
        
        if preferences_update:
            info['preferences_update'] = preferences_update
        
        return info
    
    @staticmethod
    def update_customer_profile(db: Session, client_id: str, restaurant_id: str, extracted_info: Dict) -> models.CustomerProfile:
        """Update or create customer profile with extracted information"""
        
        # Get or create profile
        # Convert client_id to string if it's a UUID
        client_id_str = str(client_id)
        profile = db.query(models.CustomerProfile).filter(
            models.CustomerProfile.client_id == client_id_str,
            models.CustomerProfile.restaurant_id == restaurant_id
        ).first()
        
        if not profile:
            profile = models.CustomerProfile(
                client_id=client_id_str,
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
        
        if 'remove_allergies' in extracted_info:
            # Remove specific allergies
            if profile.allergies:
                existing = set(profile.allergies)
                for allergy in extracted_info['remove_allergies']:
                    existing.discard(allergy)
                profile.allergies = list(existing)
                logger.info(f"Removed allergies, now: {profile.allergies}")
        
        if 'spice_preference' in extracted_info:
            profile.spice_preference = extracted_info['spice_preference']
        
        if 'preferences_update' in extracted_info:
            # Update preferences JSON
            if not profile.preferences:
                profile.preferences = {}
            profile.preferences.update(extracted_info['preferences_update'])
            logger.info(f"Updated preferences: {extracted_info['preferences_update']}")
        
        db.commit()
        return profile
    
    @staticmethod
    def get_customer_context(profile: Optional[models.CustomerProfile]) -> str:
        """Generate context string for AI about customer"""
        if not profile:
            return ""
        
        context_parts = []
        
        if profile.name:
            context_parts.append(f"Customer's name is {profile.name}")
        
        if profile.dietary_restrictions:
            context_parts.append(f"Dietary restrictions: {', '.join(profile.dietary_restrictions)}")
        
        if profile.allergies:
            context_parts.append(f"IMPORTANT - Allergies: {', '.join(profile.allergies)} (MUST avoid these ingredients)")
        
        if profile.spice_preference and profile.spice_preference != 'medium':
            context_parts.append(f"Spice preference: {profile.spice_preference}")
        
        if profile.favorite_dishes:
            context_parts.append(f"Favorite dishes: {', '.join(profile.favorite_dishes[:3])}")
        
        if profile.preferences:
            # Extract likes and dislikes
            likes = [k.replace('likes_', '').replace('_', ' ') for k, v in profile.preferences.items() if k.startswith('likes_') and v]
            dislikes = [k.replace('dislikes_', '').replace('_', ' ') for k, v in profile.preferences.items() if k.startswith('dislikes_') and v]
            if likes:
                context_parts.append(f"Likes: {', '.join(likes)}")
            if dislikes:
                context_parts.append(f"Dislikes: {', '.join(dislikes)}")
        
        if profile.order_count > 0:
            context_parts.append(f"Regular customer ({profile.order_count} orders)")
        
        return "\n".join(context_parts) if context_parts else ""
    
    @staticmethod
    def get_recommendation_context(profile: Optional[models.CustomerProfile]) -> str:
        """Generate context for AI to explain recommendations"""
        if not profile:
            return ""
        
        reasons = []
        
        if profile.allergies:
            reasons.append(f"you're allergic to {', '.join(profile.allergies)}")
        
        if profile.dietary_restrictions:
            reasons.append(f"you're {', '.join(profile.dietary_restrictions)}")
        
        if profile.spice_preference == 'mild':
            reasons.append("you prefer mild spice")
        elif profile.spice_preference in ['hot', 'extra_spicy']:
            reasons.append("you love spicy food")
        
        if profile.preferences:
            likes = [k.replace('likes_', '').replace('_', ' ') for k, v in profile.preferences.items() if k.startswith('likes_') and v]
            if likes:
                reasons.append(f"you like {', '.join(likes)}")
        
        return " and ".join(reasons) if reasons else ""