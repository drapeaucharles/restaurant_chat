"""
Simple RAG with basic memory - no complex dependencies
"""
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.chat import ChatRequest, ChatResponse
from services.mia_chat_service_hybrid import get_mia_response_hybrid, detect_language
from services.embedding_service import embedding_service
import re
import json

logger = logging.getLogger(__name__)

# Simple in-memory storage for conversations
CONVERSATION_MEMORY = {}

class SimpleMemoryRAG:
    """Simple RAG with basic memory functionality"""
    
    def __init__(self):
        self.memory = CONVERSATION_MEMORY
        self.embedding_service = embedding_service
        
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat with simple memory"""
        try:
            # Get memory key
            memory_key = f"{req.restaurant_id}:{req.client_id}"
            
            # Get or create memory
            if memory_key not in self.memory:
                self.memory[memory_key] = {
                    'history': [],
                    'name': None,
                    'preferences': []
                }
            
            client_memory = self.memory[memory_key]
            
            # Check if user is introducing themselves
            name_match = re.search(r'my name is (\w+)', req.message, re.IGNORECASE)
            if name_match:
                client_memory['name'] = name_match.group(1).capitalize()
                logger.info(f"Captured name: {client_memory['name']}")
            
            # Get restaurant info
            restaurant = db.query(text("""
                SELECT restaurant_id, data->>'name' as name
                FROM restaurants 
                WHERE restaurant_id = :rid
            """)).params(rid=req.restaurant_id).first()
            
            if not restaurant:
                return ChatResponse(
                    answer="Restaurant not found.",
                    timestamp=req.message
                )
            
            # Build context
            context = f"Restaurant: {restaurant.name}\n"
            
            # Add customer name if known
            if client_memory['name']:
                context += f"Customer name: {client_memory['name']}\n"
            
            # Add recent history (last 3 exchanges)
            if client_memory['history']:
                context += "\nRecent conversation:\n"
                for h in client_memory['history'][-3:]:
                    context += f"Customer: {h['query']}\n"
                    context += f"Assistant: {h['response'][:100]}...\n"
            
            # Get relevant menu items
            relevant_items = []
            try:
                relevant_items = self.embedding_service.search_similar_items(
                    db=db,
                    restaurant_id=req.restaurant_id,
                    query=req.message,
                    limit=5,
                    threshold=0.35
                )
            except Exception as e:
                logger.warning(f"Embedding search failed: {e}")
            
            # Add menu context if relevant
            if relevant_items and not any(word in req.message.lower() for word in ['hi', 'hello', 'name', 'call me']):
                context += "\nRelevant menu items:\n"
                for item in relevant_items[:3]:
                    context += f"- {item['name']} (${item['price']}): {item['description'][:50]}...\n"
            
            # Build prompt
            prompt = f"""{context}

Customer Query: {req.message}

Instructions:
- Be friendly and natural
- Use the customer's name if known
- Answer based on the context provided
- Keep responses concise but helpful

Response:"""
            
            # Get response
            params = {
                'max_tokens': 200,
                'temperature': 0.7,
                'timeout': 30
            }
            
            answer = get_mia_response_hybrid(prompt, params)
            
            # Store in memory
            client_memory['history'].append({
                'query': req.message,
                'response': answer
            })
            
            # Keep only last 10 exchanges
            client_memory['history'] = client_memory['history'][-10:]
            
            return ChatResponse(
                answer=answer,
                timestamp=req.message
            )
            
        except Exception as e:
            logger.error(f"Simple memory RAG error: {e}")
            # Even simpler fallback
            return ChatResponse(
                answer=f"I'm here to help! Please tell me what you'd like to know about our menu.",
                timestamp=req.message
            )

# Singleton instance
simple_memory_rag = SimpleMemoryRAG()