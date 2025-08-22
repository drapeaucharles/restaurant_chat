"""
Enhanced memory service with preference tracking and conversation summaries
"""

import os
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import text
import json

from schemas.chat import ChatRequest, ChatResponse
from services.embeddings_service import embeddings_service
from services.mia_client import get_mia_response_streaming
from services.memory_manager import memory_manager
from services.customer_preferences import preference_tracker
from services.conversation_summary import conversation_summary
from services.placeholder_remover import placeholder_remover

logger = logging.getLogger(__name__)


class EnhancedMemoryRAGService:
    """Enhanced RAG service with customer preferences and conversation summaries"""
    
    def __init__(self):
        self.context_formatter = UniversalContextFormatter()
        self.memory_manager = memory_manager
        self.preference_tracker = preference_tracker
        self.conversation_summary = conversation_summary
        self.placeholder_remover = placeholder_remover
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat request with enhanced memory features"""
        try:
            logger.info(f"Enhanced memory RAG processing for {req.restaurant_id}")
            
            # Get conversation history
            history = self.memory_manager.get_conversation(
                str(req.client_id), 
                req.restaurant_id
            )
            
            # Analyze current message for preferences
            current_prefs = self.preference_tracker.extract_preferences(req.message)
            if any(current_prefs.values()):
                self.preference_tracker.update_customer_preferences(
                    db, str(req.client_id), req.restaurant_id, current_prefs
                )
            
            # Get customer preferences
            customer_prefs = self.preference_tracker.get_customer_preferences(
                db, str(req.client_id), req.restaurant_id
            )
            
            # Get conversation history context
            history_context = self.conversation_summary.get_conversation_history_context(
                db, str(req.client_id), req.restaurant_id
            )
            
            # Get business information
            business_info = self._get_business_info(db, req.restaurant_id)
            
            # Search for relevant products/items
            search_results = []
            if business_info:
                try:
                    search_results = embeddings_service.search_similar_items(
                        query=req.message,
                        business_id=req.restaurant_id,
                        business_type=business_info.get('business_type', 'restaurant'),
                        limit=5,
                        db=db
                    )
                except Exception as e:
                    logger.warning(f"Embedding search failed: {e}, using fallback")
                    search_results = self._fallback_search(
                        req.message, req.restaurant_id, 
                        business_info.get('business_type', 'restaurant'), db
                    )
            
            # Get personalized recommendations if we have preferences
            personalized_items = []
            if customer_prefs['interaction_count'] > 0 and search_results:
                products = [item['item'] for item in search_results]
                personalized = self.preference_tracker.get_personalized_recommendations(
                    db, str(req.client_id), req.restaurant_id, products
                )
                if personalized:
                    personalized_items = personalized[:3]
            
            # Format context
            context = self.context_formatter.format_context(
                business_info=business_info,
                search_results=search_results,
                conversation_history=history,
                customer_preferences=self._format_preferences_for_context(customer_prefs),
                history_summary=history_context,
                personalized_recommendations=personalized_items,
                current_time=datetime.now()
            )
            
            # Get response from MIA
            full_response = ""
            for response in get_mia_response_streaming(
                query=req.message,
                context=context,
                model_preference=req.model_preference
            ):
                if response.answer:
                    full_response += response.answer
            
            # Remove any placeholders
            full_response = self.placeholder_remover.remove_placeholders(full_response)
            
            # Update memory with the interaction
            self.memory_manager.add_message(
                str(req.client_id),
                req.restaurant_id,
                "user",
                req.message
            )
            self.memory_manager.add_message(
                str(req.client_id),
                req.restaurant_id,
                "assistant",
                full_response
            )
            
            # Check if we should summarize this conversation
            current_conversation = self.memory_manager.get_conversation(
                str(req.client_id), 
                req.restaurant_id
            )
            
            if self.conversation_summary.should_summarize_conversation(current_conversation):
                summary = self.conversation_summary.create_conversation_summary(
                    current_conversation,
                    business_info.get('business_type', 'restaurant')
                )
                self.conversation_summary.save_conversation_summary(
                    db, str(req.client_id), req.restaurant_id, summary
                )
            
            return ChatResponse(answer=full_response)
            
        except Exception as e:
            logger.error(f"Enhanced memory RAG error: {str(e)}")
            return ChatResponse(
                answer="I apologize, but I'm having trouble processing your request. Please try again."
            )
    
    def _get_business_info(self, db: Session, business_id: str) -> Optional[Dict[str, Any]]:
        """Get business information from database"""
        try:
            # Try businesses table first
            query = text("""
                SELECT business_id, name, business_type, description, 
                       data, metadata, opening_hours
                FROM businesses 
                WHERE business_id = :business_id
            """)
            result = db.execute(query, {"business_id": business_id}).fetchone()
            
            if result:
                return {
                    'business_id': result[0],
                    'name': result[1],
                    'business_type': result[2],
                    'description': result[3],
                    'data': result[4] or {},
                    'metadata': result[5] or {},
                    'opening_hours': result[6]
                }
            
            # Fallback to restaurants table
            query = text("""
                SELECT restaurant_id, name, cuisine_type, restaurant_story,
                       phone, address, opening_hours
                FROM restaurants 
                WHERE restaurant_id = :restaurant_id
            """)
            result = db.execute(query, {"restaurant_id": business_id}).fetchone()
            
            if result:
                return {
                    'business_id': result[0],
                    'name': result[1],
                    'business_type': 'restaurant',
                    'description': result[3],
                    'data': {
                        'cuisine_type': result[2],
                        'phone': result[4],
                        'address': result[5]
                    },
                    'metadata': {},
                    'opening_hours': result[6]
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting business info: {e}")
            return None
    
    def _fallback_search(
        self, 
        query: str, 
        business_id: str, 
        business_type: str,
        db: Session
    ) -> List[Dict[str, Any]]:
        """Fallback text-based search"""
        try:
            search_terms = query.lower().split()
            
            if business_type == 'restaurant':
                # Search menu items
                conditions = []
                for term in search_terms[:3]:  # Limit to 3 terms
                    conditions.append(
                        f"(LOWER(name) LIKE '%{term}%' OR LOWER(description) LIKE '%{term}%')"
                    )
                
                where_clause = " OR ".join(conditions)
                query_text = f"""
                    SELECT item_id, name, description, category, price
                    FROM menu_items
                    WHERE restaurant_id = :business_id
                    AND ({where_clause})
                    LIMIT 5
                """
                
                results = db.execute(text(query_text), {"business_id": business_id}).fetchall()
                
                return [{
                    'item': {
                        'item_id': r[0],
                        'name': r[1],
                        'description': r[2],
                        'category': r[3],
                        'price': float(r[4]) if r[4] else 0
                    },
                    'similarity': 0.7  # Fixed similarity for text search
                } for r in results]
            else:
                # Search products for other business types
                conditions = []
                for term in search_terms[:3]:
                    conditions.append(
                        f"(LOWER(name) LIKE '%{term}%' OR LOWER(description) LIKE '%{term}%')"
                    )
                
                where_clause = " OR ".join(conditions)
                query_text = f"""
                    SELECT product_id, name, description, category, price, metadata
                    FROM products
                    WHERE business_id = :business_id
                    AND ({where_clause})
                    LIMIT 5
                """
                
                results = db.execute(text(query_text), {"business_id": business_id}).fetchall()
                
                return [{
                    'item': {
                        'product_id': r[0],
                        'name': r[1],
                        'description': r[2],
                        'category': r[3],
                        'price': float(r[4]) if r[4] else 0,
                        'metadata': r[5] or {}
                    },
                    'similarity': 0.7
                } for r in results]
                
        except Exception as e:
            logger.error(f"Fallback search error: {e}")
            return []
    
    def _format_preferences_for_context(self, prefs: Dict[str, Any]) -> str:
        """Format preferences for AI context"""
        parts = []
        
        if prefs.get('dietary'):
            parts.append(f"Dietary: {', '.join(prefs['dietary'])}")
        
        if prefs.get('preferences'):
            parts.append(f"Preferences: {', '.join(prefs['preferences'])}")
        
        if prefs.get('services'):
            parts.append(f"Services: {', '.join(prefs['services'])}")
        
        if prefs.get('interaction_count', 0) > 1:
            parts.append(f"Returning customer ({prefs['interaction_count']} visits)")
        
        return " | ".join(parts) if parts else "New customer"


class UniversalContextFormatter:
    """Format context for any business type with enhanced features"""
    
    def format_context(
        self,
        business_info: Dict[str, Any],
        search_results: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]],
        customer_preferences: str,
        history_summary: str,
        personalized_recommendations: List[Dict[str, Any]],
        current_time: datetime
    ) -> str:
        """Format enhanced context for the AI"""
        
        business_type = business_info.get('business_type', 'restaurant')
        business_name = business_info.get('name', 'our business')
        
        # Build context parts
        context_parts = []
        
        # Business context
        context_parts.append(f"You are an AI assistant for {business_name}, a {business_type}.")
        
        if business_info.get('description'):
            context_parts.append(f"About us: {business_info['description']}")
        
        # Customer context
        if customer_preferences:
            context_parts.append(f"Customer profile: {customer_preferences}")
        
        if history_summary:
            context_parts.append(f"History: {history_summary}")
        
        # Personalized recommendations
        if personalized_recommendations:
            context_parts.append("\nPersonalized recommendations based on preferences:")
            for rec in personalized_recommendations[:3]:
                item = rec['product']
                reasons = ', '.join(rec['reasons'])
                context_parts.append(
                    f"- {item['name']}: {item.get('description', 'No description')} "
                    f"(Recommended because: {reasons})"
                )
        
        # Regular search results
        if search_results:
            context_parts.append(f"\nRelevant {self._get_item_type(business_type)}:")
            for result in search_results[:5]:
                item = result['item']
                context_parts.append(self._format_item(item, business_type))
        
        # Conversation history
        if conversation_history:
            context_parts.append("\nRecent conversation:")
            for msg in conversation_history[-3:]:  # Last 3 messages
                role = "Customer" if msg['role'] == 'user' else "You"
                context_parts.append(f"{role}: {msg['content']}")
        
        # Time context
        context_parts.append(f"\nCurrent time: {current_time.strftime('%A, %B %d at %I:%M %p')}")
        
        # Instructions
        context_parts.append(
            f"\nProvide helpful, personalized responses. "
            f"Use the customer's preferences and history to make relevant suggestions. "
            f"Be natural and conversational. "
            f"If you mention any items, use their exact names from the context."
        )
        
        return "\n".join(context_parts)
    
    def _get_item_type(self, business_type: str) -> str:
        """Get the item type name for a business"""
        if business_type == 'restaurant':
            return "menu items"
        elif business_type == 'legal_visa':
            return "services"
        elif business_type == 'salon':
            return "services"
        elif business_type == 'hotel':
            return "rooms and services"
        else:
            return "products/services"
    
    def _format_item(self, item: Dict[str, Any], business_type: str) -> str:
        """Format an item based on business type"""
        name = item.get('name', 'Unknown')
        description = item.get('description', '')
        price = item.get('price', 0)
        
        if business_type == 'restaurant':
            category = item.get('category', 'General')
            return f"- {name} ({category}): {description} - ${price:.2f}"
        elif business_type == 'legal_visa':
            duration = item.get('metadata', {}).get('duration', '')
            return f"- {name}: {description} - ${price:.2f} {duration}"
        else:
            return f"- {name}: {description} - ${price:.2f}"


# Create service instance
enhanced_memory_rag = EnhancedMemoryRAGService()