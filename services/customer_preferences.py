"""
Customer preference tracking service
Tracks and learns from customer interactions
"""

from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import text
import json
import re
import logging

logger = logging.getLogger(__name__)


class CustomerPreferenceTracker:
    """Track and analyze customer preferences from conversations"""
    
    # Preference patterns
    DIETARY_PATTERNS = {
        'vegetarian': r'\b(vegetarian|veggie|no meat|meatless)\b',
        'vegan': r'\b(vegan|no animal|plant-based)\b',
        'gluten_free': r'\b(gluten[\s-]?free|no gluten|celiac)\b',
        'dairy_free': r'\b(dairy[\s-]?free|no dairy|lactose[\s-]?free)\b',
        'halal': r'\b(halal)\b',
        'kosher': r'\b(kosher)\b',
        'nut_free': r'\b(nut[\s-]?free|no nuts|nut allergy)\b',
        'spicy': r'\b(spicy|hot|chili|pepper)\b',
        'mild': r'\b(mild|not spicy|no spice)\b'
    }
    
    PREFERENCE_PATTERNS = {
        'healthy': r'\b(healthy|nutritious|light|low[\s-]?cal|diet)\b',
        'comfort': r'\b(comfort|hearty|filling|rich)\b',
        'quick': r'\b(quick|fast|rapid|hurry)\b',
        'special_occasion': r'\b(special|celebrate|anniversary|birthday)\b',
        'budget': r'\b(budget|cheap|affordable|value)\b',
        'premium': r'\b(premium|luxury|best|finest)\b'
    }
    
    SERVICE_PATTERNS = {
        'delivery': r'\b(deliver|delivery|bring|send)\b',
        'takeout': r'\b(takeout|take[\s-]?away|pickup|collect)\b',
        'dine_in': r'\b(dine[\s-]?in|restaurant|table|seat)\b',
        'catering': r'\b(cater|event|party|group)\b'
    }
    
    def __init__(self):
        self.preference_cache = {}  # In-memory cache
    
    def extract_preferences(self, message: str) -> Dict[str, List[str]]:
        """Extract preferences from a message"""
        message_lower = message.lower()
        preferences = {
            'dietary': [],
            'preferences': [],
            'services': []
        }
        
        # Check dietary restrictions
        for diet, pattern in self.DIETARY_PATTERNS.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                preferences['dietary'].append(diet)
        
        # Check general preferences
        for pref, pattern in self.PREFERENCE_PATTERNS.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                preferences['preferences'].append(pref)
        
        # Check service preferences
        for service, pattern in self.SERVICE_PATTERNS.items():
            if re.search(pattern, message_lower, re.IGNORECASE):
                preferences['services'].append(service)
        
        return preferences
    
    def update_customer_preferences(
        self,
        db: Session,
        client_id: str,
        business_id: str,
        preferences: Dict[str, List[str]]
    ):
        """Update customer preferences in database"""
        try:
            # Create table if not exists
            create_table = text("""
                CREATE TABLE IF NOT EXISTS customer_preferences (
                    client_id UUID,
                    business_id VARCHAR(255),
                    preferences JSONB,
                    interaction_count INT DEFAULT 1,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    PRIMARY KEY (client_id, business_id)
                )
            """)
            db.execute(create_table)
            db.commit()
            
            # Get existing preferences
            get_query = text("""
                SELECT preferences, interaction_count 
                FROM customer_preferences 
                WHERE client_id = :client_id::uuid 
                AND business_id = :business_id
            """)
            
            result = db.execute(get_query, {
                "client_id": client_id,
                "business_id": business_id
            }).fetchone()
            
            if result:
                # Merge preferences
                existing = result[0] or {}
                interaction_count = result[1] + 1
                
                # Update counts for each preference
                for category, items in preferences.items():
                    if category not in existing:
                        existing[category] = {}
                    
                    for item in items:
                        if item not in existing[category]:
                            existing[category][item] = 0
                        existing[category][item] += 1
                
                # Update record
                update_query = text("""
                    UPDATE customer_preferences 
                    SET preferences = :preferences,
                        interaction_count = :count,
                        last_updated = CURRENT_TIMESTAMP
                    WHERE client_id = :client_id::uuid 
                    AND business_id = :business_id
                """)
                
                db.execute(update_query, {
                    "preferences": json.dumps(existing),
                    "count": interaction_count,
                    "client_id": client_id,
                    "business_id": business_id
                })
            else:
                # Create new record
                new_prefs = {}
                for category, items in preferences.items():
                    new_prefs[category] = {item: 1 for item in items}
                
                insert_query = text("""
                    INSERT INTO customer_preferences 
                    (client_id, business_id, preferences, interaction_count)
                    VALUES (:client_id::uuid, :business_id, :preferences, 1)
                """)
                
                db.execute(insert_query, {
                    "client_id": client_id,
                    "business_id": business_id,
                    "preferences": json.dumps(new_prefs)
                })
            
            db.commit()
            
            # Update cache
            cache_key = f"{client_id}:{business_id}"
            self.preference_cache[cache_key] = preferences
            
        except Exception as e:
            logger.error(f"Error updating customer preferences: {str(e)}")
            db.rollback()
    
    def get_customer_preferences(
        self,
        db: Session,
        client_id: str,
        business_id: str
    ) -> Dict[str, Any]:
        """Get customer preferences"""
        # Check cache first
        cache_key = f"{client_id}:{business_id}"
        if cache_key in self.preference_cache:
            return self.preference_cache[cache_key]
        
        try:
            query = text("""
                SELECT preferences, interaction_count, last_updated
                FROM customer_preferences 
                WHERE client_id = :client_id::uuid 
                AND business_id = :business_id
            """)
            
            result = db.execute(query, {
                "client_id": client_id,
                "business_id": business_id
            }).fetchone()
            
            if result:
                preferences = result[0] or {}
                
                # Get top preferences
                top_prefs = {
                    'dietary': self._get_top_items(preferences.get('dietary', {})),
                    'preferences': self._get_top_items(preferences.get('preferences', {})),
                    'services': self._get_top_items(preferences.get('services', {})),
                    'interaction_count': result[1],
                    'last_updated': result[2].isoformat() if result[2] else None
                }
                
                # Cache it
                self.preference_cache[cache_key] = top_prefs
                return top_prefs
            
            return {
                'dietary': [],
                'preferences': [],
                'services': [],
                'interaction_count': 0
            }
            
        except Exception as e:
            logger.error(f"Error getting customer preferences: {str(e)}")
            return {
                'dietary': [],
                'preferences': [],
                'services': [],
                'interaction_count': 0
            }
    
    def _get_top_items(self, items_dict: Dict[str, int], limit: int = 3) -> List[str]:
        """Get top items by count"""
        if not items_dict:
            return []
        
        sorted_items = sorted(items_dict.items(), key=lambda x: x[1], reverse=True)
        return [item[0] for item in sorted_items[:limit]]
    
    def analyze_conversation_for_preferences(
        self,
        db: Session,
        client_id: str,
        business_id: str,
        messages: List[Dict[str, Any]]
    ):
        """Analyze a conversation for preferences"""
        all_preferences = {
            'dietary': [],
            'preferences': [],
            'services': []
        }
        
        # Analyze each customer message
        for msg in messages:
            if msg.get('sender_type') == 'client':
                prefs = self.extract_preferences(msg.get('message', ''))
                for category, items in prefs.items():
                    all_preferences[category].extend(items)
        
        # Remove duplicates
        for category in all_preferences:
            all_preferences[category] = list(set(all_preferences[category]))
        
        # Update if we found any preferences
        if any(all_preferences.values()):
            self.update_customer_preferences(
                db, client_id, business_id, all_preferences
            )
    
    def get_preference_context(
        self,
        db: Session,
        client_id: str,
        business_id: str
    ) -> str:
        """Get preference context for AI"""
        prefs = self.get_customer_preferences(db, client_id, business_id)
        
        if prefs['interaction_count'] == 0:
            return ""
        
        context_parts = []
        
        if prefs['dietary']:
            context_parts.append(f"Dietary preferences: {', '.join(prefs['dietary'])}")
        
        if prefs['preferences']:
            context_parts.append(f"Usually prefers: {', '.join(prefs['preferences'])}")
        
        if prefs['services']:
            context_parts.append(f"Service preferences: {', '.join(prefs['services'])}")
        
        if prefs['interaction_count'] > 1:
            context_parts.append(f"Returning customer ({prefs['interaction_count']} visits)")
        
        return " | ".join(context_parts) if context_parts else ""
    
    def get_personalized_recommendations(
        self,
        db: Session,
        client_id: str,
        business_id: str,
        products: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Get personalized product recommendations based on preferences"""
        prefs = self.get_customer_preferences(db, client_id, business_id)
        
        scored_products = []
        for product in products:
            score = 0
            reasons = []
            
            product_text = f"{product.get('name', '')} {product.get('description', '')}".lower()
            
            # Check dietary matches
            for diet in prefs['dietary']:
                if diet in product_text or (product.get('dietary_info') and diet in product.get('dietary_info', [])):
                    score += 3
                    reasons.append(f"matches {diet} preference")
            
            # Check preference matches
            for pref in prefs['preferences']:
                if pref == 'healthy' and any(word in product_text for word in ['healthy', 'light', 'fresh']):
                    score += 2
                    reasons.append("healthy option")
                elif pref == 'comfort' and any(word in product_text for word in ['hearty', 'rich', 'comfort']):
                    score += 2
                    reasons.append("comfort food")
                elif pref == 'budget' and product.get('price', 999) < 15:
                    score += 2
                    reasons.append("budget friendly")
                elif pref == 'premium' and any(word in product_text for word in ['premium', 'finest', 'luxury']):
                    score += 2
                    reasons.append("premium selection")
            
            if score > 0:
                scored_products.append({
                    'product': product,
                    'score': score,
                    'reasons': reasons
                })
        
        # Sort by score
        scored_products.sort(key=lambda x: x['score'], reverse=True)
        
        return scored_products[:5]  # Return top 5


# Global instance
preference_tracker = CustomerPreferenceTracker()