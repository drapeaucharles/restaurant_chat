"""
Enhanced RAG Chat Service v3 with lazy Redis import
Works with or without Redis installed
"""
import logging
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text

from services.mia_chat_service_hybrid import (
    mia_chat_service_hybrid,
    HybridQueryClassifier,
    QueryType,
    get_hybrid_parameters,
    get_mia_response_hybrid,
    detect_language,
    get_persona_name
)
from services.embedding_service import embedding_service
from services.response_length_manager import ResponseLengthManager
from services.response_validator import response_validator
from services.allergen_service import allergen_service
from services.conversation_memory_enhanced_lazy import enhanced_conversation_memory
from services.context_formatter import context_formatter, ContextSection
from schemas.chat import ChatRequest, ChatResponse
import models

logger = logging.getLogger(__name__)

class EnhancedRAGChatV3:
    """Enhanced RAG with full conversation memory"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.conversation_memory = enhanced_conversation_memory
        self.similarity_threshold = 0.25
        self.max_context_items = 15
    
    def build_context_with_memory(self, 
                                 db: Session,
                                 restaurant_id: str, 
                                 client_id: str,
                                 query: str, 
                                 query_type: QueryType) -> Dict[ContextSection, str]:
        """Build comprehensive context including conversation memory"""
        
        context_sections = {}
        
        # Get customer info from memory
        customer_info = self.conversation_memory.extract_customer_info(restaurant_id, client_id)
        
        # Add personalization if we know the customer
        if customer_info['name'] or customer_info['preferences']:
            personal_context = []
            if customer_info['name']:
                personal_context.append(f"Customer name: {customer_info['name']}")
            if customer_info['dietary_restrictions']:
                personal_context.append(f"Dietary restrictions: {', '.join(customer_info['dietary_restrictions'])}")
            if customer_info['topics']:
                personal_context.append(f"Has asked about: {', '.join(customer_info['topics'][:3])}")
            
            context_sections[ContextSection.PERSONALIZATION] = "\n".join(personal_context)
        
        # Add conversation history
        conv_context = self.conversation_memory.get_context(restaurant_id, client_id)
        if conv_context:
            context_sections[ContextSection.CONVERSATION_HISTORY] = conv_context
        
        # Skip menu search for simple greetings
        # Removed GREETING special case - let AI handle naturally

        if False:  # was query_type == QueryType.GREETING

            pass
            
            if relevant_items:
                # Check for allergen queries
                query_lower = query.lower()
                is_allergen_query = any(word in query_lower for word in [
                    'allerg', 'nut', 'dairy', 'gluten', 'shellfish', 'vegetarian', 'vegan'
                ])
                
                if is_allergen_query:
                    # Use allergen service for better filtering
                    allergen_data = allergen_service.get_items_for_restriction(db, restaurant_id, query_lower)
                    if allergen_data['safe_items']:
                        menu_context = f"Items suitable for {allergen_data['restriction_type']}:\n"
                        for item in allergen_data['safe_items'][:10]:
                            menu_context += f"- {item['name']} (${item['price']}): {item['description'][:60]}...\n"
                        context_sections[ContextSection.MENU_ITEMS] = menu_context
                else:
                    # Regular menu items
                    menu_context = "Relevant menu items:\n"
                    for item in relevant_items:
                        desc = item.get('description', '')[:60]
                        menu_context += f"- {item['name']} (${item['price']}): {desc}...\n"
                    context_sections[ContextSection.MENU_ITEMS] = menu_context
        
        except Exception as e:
            logger.warning(f"Error getting menu items: {e}")
        
        # Add restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == restaurant_id
        ).first()
        
        if restaurant and restaurant.data:
            rest_info = []
            data = restaurant.data
            if 'cuisine_type' in data:
                rest_info.append(f"Cuisine: {data['cuisine_type']}")
            if 'hours' in data:
                rest_info.append(f"Hours: {data['hours']}")
            if rest_info:
                context_sections[ContextSection.RESTAURANT_INFO] = "\n".join(rest_info)
        
        return context_sections
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat request with full conversation memory"""
        
        logger.info(f"Enhanced RAG v3 - Processing: '{req.message[:50]}...'")
        
        # Skip AI for restaurant messages
        if req.sender_type == 'restaurant':
            return ChatResponse(answer="")
        
        # Classify query
        query_type = HybridQueryClassifier.classify(req.message)
        language = detect_language(req.message)
        
        # Get restaurant info
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if not restaurant:
            return ChatResponse(answer="Restaurant not found.")
        
        business_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
        
        # Build context with memory
        context_sections = self.build_context_with_memory(
            db, req.restaurant_id, req.client_id, req.message, query_type
        )
        
        # Create system prompt
        persona_name = get_persona_name(language)
        system_prompt = f"""You are {persona_name}, a friendly AI assistant for {business_name}.

IMPORTANT RULES:
1. If you know the customer's name, use it naturally in your responses
2. Remember their preferences and dietary restrictions
3. Only recommend items that exist in the menu context
4. Be warm and conversational while staying professional
5. Keep responses concise but helpful
6. Always respond in {language}"""
        
        # Format the full prompt
        full_prompt = context_formatter.format_prompt_with_context(
            system_prompt=system_prompt,
            context_sections=context_sections,
            customer_message=req.message,
            assistant_name=persona_name
        )
        
        # Get response parameters
        params = get_hybrid_parameters(query_type)
        
        # Adjust for personalized responses
        if context_sections.get(ContextSection.PERSONALIZATION):
            params['temperature'] = 0.8  # Slightly more creative for personalized responses
        
        # Get AI response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Validate response
        answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
        
        # Store in conversation memory
        metadata = {
            'query_type': query_type.value,
            'language': language,
            'had_menu_context': bool(context_sections.get(ContextSection.MENU_ITEMS))
        }
        
        self.conversation_memory.add_turn(
            req.restaurant_id, 
            req.client_id, 
            req.message, 
            answer, 
            metadata
        )
        
        # Save to database
        new_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(new_message)
        db.commit()
        
        return ChatResponse(
            answer=answer,
            timestamp=req.message
        )

# Create singleton instance
enhanced_rag_chat_v3 = EnhancedRAGChatV3()