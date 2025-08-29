"""
Enhanced RAG Chat Service v3 with DEBUG logging
This version logs everything to help diagnose memory issues
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

class EnhancedRAGChatV3Debug:
    """Enhanced RAG with DEBUG logging for memory issues"""
    
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
        
        logger.info(f"DEBUG: Building context for {restaurant_id}/{client_id}")
        context_sections = {}
        
        # Get customer info from memory
        customer_info = self.conversation_memory.extract_customer_info(restaurant_id, client_id)
        logger.info(f"DEBUG: Extracted customer info: {customer_info}")
        
        # Get conversation history
        history = self.conversation_memory.get_history(restaurant_id, client_id)
        logger.info(f"DEBUG: Found {len(history)} history items")
        
        # Add personalization if we know the customer
        if customer_info['name'] or customer_info['preferences']:
            personal_context = []
            if customer_info['name']:
                personal_context.append(f"Customer name: {customer_info['name']}")
                logger.info(f"DEBUG: Adding customer name to context: {customer_info['name']}")
            if customer_info['dietary_restrictions']:
                personal_context.append(f"Dietary restrictions: {', '.join(customer_info['dietary_restrictions'])}")
            if customer_info['topics']:
                personal_context.append(f"Has asked about: {', '.join(customer_info['topics'][:3])}")
            
            context_sections[ContextSection.PERSONALIZATION] = "\n".join(personal_context)
            logger.info(f"DEBUG: Personalization context: {personal_context}")
        else:
            logger.info("DEBUG: No personalization info found")
        
        # Add conversation history
        conv_context = self.conversation_memory.get_context(restaurant_id, client_id)
        if conv_context:
            context_sections[ContextSection.CONVERSATION_HISTORY] = conv_context
            logger.info(f"DEBUG: Added conversation history to context")
        else:
            logger.info("DEBUG: No conversation history found")
        
        # Skip menu search for simple greetings
        # Removed GREETING special case - let AI handle naturally

        if False:  # was query_type == QueryType.GREETING

            pass
            
            if relevant_items:
                logger.info(f"DEBUG: Found {len(relevant_items)} relevant menu items")
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
            else:
                logger.info("DEBUG: No relevant menu items found")
        
        except Exception as e:
            logger.error(f"DEBUG: Error getting menu items: {e}")
        
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
        
        logger.info(f"DEBUG: Final context sections: {list(context_sections.keys())}")
        return context_sections
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat request with DEBUG logging"""
        
        logger.info(f"DEBUG: Processing message from {req.client_id}: '{req.message[:50]}...'")
        
        # Skip AI for restaurant messages
        if req.sender_type == 'restaurant':
            return ChatResponse(answer="")
        
        # IMPORTANT: Store the message BEFORE building context for next time
        # This ensures name extraction happens before we need it
        import re
        name_match = re.search(r'my name is (\w+)', req.message, re.IGNORECASE)
        if name_match:
            # Pre-store just the name for immediate use
            customer_name = name_match.group(1).capitalize()
            logger.info(f"DEBUG: Detected name introduction: {customer_name}")
        else:
            customer_name = None
        
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
        
        # Get customer info for enhanced prompt
        customer_info = self.conversation_memory.extract_customer_info(req.restaurant_id, req.client_id)
        
        # If we just detected a name, use it immediately
        if customer_name and not customer_info['name']:
            customer_info['name'] = customer_name
            logger.info(f"DEBUG: Using immediately detected name: {customer_name}")
        
        # Create system prompt
        persona_name = get_persona_name(language)
        
        # Build prompt based on what we know
        if customer_info['name']:
            system_prompt = f"""You are {persona_name}, a friendly AI assistant for {business_name}.

The customer's name is {customer_info['name']}. Use their name naturally in your response.
Be warm, personal, and helpful."""
            logger.info(f"DEBUG: Using personalized prompt with name: {customer_info['name']}")
        else:
            system_prompt = f"""You are {persona_name}, a friendly AI assistant for {business_name}.

Be warm and helpful. If the customer introduces themselves, acknowledge their name warmly."""
            logger.info("DEBUG: Using generic prompt (no name known)")
        
        # Add dietary preferences if known
        if customer_info['dietary_restrictions']:
            system_prompt += f"\n\nIMPORTANT: This customer has mentioned they are {', '.join(customer_info['dietary_restrictions'])}. Keep this in mind for recommendations."
        
        # Add general rules
        system_prompt += f"""

RULES:
1. Only recommend items that exist in the menu context provided
2. Be conversational and natural
3. Keep responses concise but helpful
4. Always respond in {language}"""
        
        # Format the full prompt
        full_prompt = context_formatter.format_prompt_with_context(
            system_prompt=system_prompt,
            context_sections=context_sections,
            customer_message=req.message,
            assistant_name=persona_name
        )
        
        logger.info(f"DEBUG: Full prompt length: {len(full_prompt)} chars")
        logger.info(f"DEBUG: Context sections included: {list(context_sections.keys())}")
        
        # Get response parameters
        params = get_hybrid_parameters(query_type)
        
        # Adjust for personalized responses
        if context_sections.get(ContextSection.PERSONALIZATION) or customer_name:
            params['temperature'] = 0.8  # Slightly more creative for personalized responses
        
        # Get AI response
        answer = get_mia_response_hybrid(full_prompt, params)
        
        # Validate response
        answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
        
        # Store in conversation memory AFTER getting response
        metadata = {
            'query_type': query_type.value,
            'language': language,
            'had_menu_context': bool(context_sections.get(ContextSection.MENU_ITEMS))
        }
        
        logger.info(f"DEBUG: Storing conversation turn in memory")
        self.conversation_memory.add_turn(
            req.restaurant_id, 
            req.client_id, 
            req.message, 
            answer, 
            metadata
        )
        
        # Verify storage
        post_storage_history = self.conversation_memory.get_history(req.restaurant_id, req.client_id)
        logger.info(f"DEBUG: After storage, history has {len(post_storage_history)} items")
        
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
enhanced_rag_chat_v3_debug = EnhancedRAGChatV3Debug()