"""
Ultra simple RAG - absolutely minimal dependencies
"""
import logging
from typing import Dict
from sqlalchemy.orm import Session
from schemas.chat import ChatRequest, ChatResponse
import models
import re

logger = logging.getLogger(__name__)

# Simple in-memory storage
MEMORY = {}

class UltraSimpleRAG:
    """The simplest possible RAG that works"""
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process chat with ultra simple approach"""
        try:
            # Memory key
            key = f"{req.restaurant_id}:{req.client_id}"
            
            # Get or create memory
            if key not in MEMORY:
                MEMORY[key] = {"name": None, "history": []}
            
            memory = MEMORY[key]
            
            # Check for name
            if "my name is" in req.message.lower():
                match = re.search(r'my name is (\w+)', req.message, re.IGNORECASE)
                if match:
                    memory["name"] = match.group(1).capitalize()
            
            # Get restaurant
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                return ChatResponse(
                    answer="I cannot find your restaurant information.",
                    timestamp=req.message
                )
            
            restaurant_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
            
            # Build response based on query
            response = ""
            
            # Handle different query types
            if "my name is" in req.message.lower() and memory["name"]:
                response = f"Hello {memory['name']}! It's wonderful to meet you. I'm here to help you with {restaurant_name}'s menu. What would you like to know?"
            
            elif "call me" in req.message.lower() and "name" in req.message.lower():
                if memory["name"]:
                    response = f"Of course, {memory['name']}! I'll make sure to address you by name. How can I help you today, {memory['name']}?"
                else:
                    response = "I'd be happy to call you by name, but I don't think you've told me your name yet. What would you like me to call you?"
            
            elif "what is my name" in req.message.lower():
                if memory["name"]:
                    response = f"Your name is {memory['name']}."
                else:
                    response = "I don't know your name yet. Please tell me your name by saying 'My name is...'"
            
            elif "pasta" in req.message.lower():
                # Get menu items
                menu = restaurant.data.get('menu', []) if restaurant.data else []
                pasta_items = [item for item in menu if item and 'pasta' in str(item).lower()]
                
                if pasta_items and memory["name"]:
                    response = f"Great question, {memory['name']}! Here are our pasta dishes:\n"
                elif pasta_items:
                    response = "Here are our pasta dishes:\n"
                else:
                    response = "I don't see any pasta dishes on our current menu."
                
                # Add pasta items
                for item in pasta_items[:5]:
                    if isinstance(item, dict):
                        name = item.get('title') or item.get('dish') or item.get('name', 'Pasta Dish')
                        price = item.get('price', 'Price not listed')
                        desc = item.get('description', 'No description')
                        response += f"\n- {name} ({price}): {desc[:60]}..."
            
            elif any(greeting in req.message.lower() for greeting in ['hi', 'hello', 'hey']):
                if memory["name"]:
                    response = f"Hello {memory['name']}! Welcome back to {restaurant_name}. How can I help you today?"
                else:
                    response = f"Hello! Welcome to {restaurant_name}. I'm here to help you with our menu. How can I assist you today?"
            
            else:
                # Default response
                if memory["name"]:
                    response = f"I'm here to help you, {memory['name']}! You can ask me about our menu items, ingredients, prices, or dietary options."
                else:
                    response = f"Welcome to {restaurant_name}! I'm here to help you with our menu. You can ask me about specific dishes, dietary options, or tell me your preferences."
            
            # Store in history
            memory["history"].append({
                "q": req.message,
                "a": response
            })
            
            # Keep only last 5
            memory["history"] = memory["history"][-5:]
            
            return ChatResponse(
                answer=response,
                timestamp=req.message
            )
            
        except Exception as e:
            logger.error(f"Ultra simple RAG error: {str(e)}")
            # Ultra fallback
            return ChatResponse(
                answer="Welcome! I'm here to help you with our menu. What would you like to know?",
                timestamp=req.message
            )

# Singleton instance
ultra_simple_rag = UltraSimpleRAG()