"""
Improved MIA Chat Service with flexible AI responses and better context handling
"""
import requests
import json
import re
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import models
from pinecone_utils import query_pinecone
from schemas.chat import ChatRequest, ChatResponse
from schemas.restaurant import RestaurantData
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from services.restaurant_service import apply_menu_fallbacks
from services.simple_response_cache import response_cache
import os
import logging

logger = logging.getLogger(__name__)

# MIA Backend URL - can be configured via environment variable
MIA_BACKEND_URL = os.getenv("MIA_BACKEND_URL", "https://mia-backend-production.up.railway.app")
MIA_LOCAL_URL = os.getenv("MIA_LOCAL_URL", "http://localhost:8000")

# Super simple system prompt
system_prompt = """You are a friendly restaurant assistant. Be helpful and concise. Respond in the customer's language."""

def format_menu_context_structured(menu_items, restaurant_data):
    """Simple menu formatting"""
    
    # Just list menu items simply
    lines = []
    lines.append(f"Restaurant: {restaurant_data.get('restaurant_name', '')}")
    lines.append("\nMenu:")
    
    for item in menu_items[:30]:  # Limit items
        name = item.get('dish') or item.get('name', '')
        price = item.get('price', '')
        category = item.get('subcategory', 'main')
        if name:
            lines.append(f"- {name} ({price}) [{category}]")
    
    return "\n".join(lines)

def format_conversation_context(recent_messages):
    """Format recent conversation history for better continuity"""
    if not recent_messages or len(recent_messages) == 0:
        return ""
    
    # Only include if there's actual conversation history (more than just the current message)
    if len(recent_messages) <= 1:
        return ""
    
    conversation = []
    for msg in recent_messages[:-1]:  # Exclude the current message
        role = "Customer" if msg.sender_type == "client" else "You"
        conversation.append(f"{role}: {msg.message}")
    
    if conversation:
        return "Previous messages in THIS conversation:\n" + "\n".join(conversation)
    return ""



def get_mia_response_improved(prompt: str, temperature: float = 0.7, max_tokens: int = 400) -> str:
    """Get response from MIA with improved parameters"""
    try:
        # Skip local MIA if configured (due to instruction-following issues)
        skip_local = os.getenv("SKIP_LOCAL_MIA", "true").lower() == "true"
        
        if not skip_local:
            # Try local MIA instance first
            try:
                response = requests.post(
                    f"{MIA_LOCAL_URL}/generate",
                    json={
                        "prompt": prompt,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                        "restaurant_mode": True,
                        "top_p": 0.9,  # Add nucleus sampling for better diversity
                        "frequency_penalty": 0.3,  # Reduce repetition
                        "presence_penalty": 0.3   # Encourage covering more topics
                    },
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("text", "I'm having trouble understanding. Could you please rephrase?")
            except:
                logger.info("Local MIA not available, trying remote")
        
        # Use remote MIA backend
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json={
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": temperature,
                "source": "restaurant-improved",
                "top_p": 0.9,
                "frequency_penalty": 0.3,
                "presence_penalty": 0.3
            },
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend-improved"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            text = result.get("text", result.get("response", ""))
            logger.info(f"MIA response received: {text[:100]}...")
            if not text:
                logger.warning("MIA returned empty response")
                return "I'm having trouble understanding. Could you please rephrase?"
            return text
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            return "I apologize, but I'm having technical difficulties. Please try again in a moment or ask our staff for assistance."
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "I'm taking a bit longer to respond. Please try again."
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}")
        return "I'm experiencing technical difficulties. Please try again or ask our staff for help."

def mia_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Improved chat service with better context handling and natural responses"""
    
    logger.info(f"MIA CHAT SERVICE (Improved) - Restaurant: {req.restaurant_id}, Client: {req.client_id}")
    logger.info(f"Query: '{req.message}'")
    
    # Get restaurant
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        logger.error(f"Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    # Skip AI for restaurant staff messages
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Get or create client
    phone_number = getattr(req, 'phone_number', None)
    client = get_or_create_client(db, req.client_id, req.restaurant_id, phone_number)
    
    try:
        # Get restaurant data
        data = restaurant.data or {}
        menu_items = data.get("menu", [])
        
        # Apply menu fallbacks if available
        if menu_items:
            try:
                menu_items = apply_menu_fallbacks(menu_items)
            except Exception as e:
                logger.warning(f"Error applying menu fallbacks: {e}")
        
        # Build context - simple and complete
        context_parts = []
        
        # 1. System instruction (simple and flexible)
        context_parts.append(system_prompt)
        
        # 2. Full restaurant context (let AI decide what's relevant)
        restaurant_context = format_menu_context_structured(menu_items, data)
        context_parts.append(restaurant_context)
        
        # 3. Recent conversation history for continuity
        # TEMPORARILY DISABLED: Conversation history causing confusion
        # recent_messages = fetch_recent_chat_history(db, req.client_id, req.restaurant_id)
        # conv_context = format_conversation_context(recent_messages)
        # if conv_context:
        #     context_parts.append(conv_context)
        
        # 4. Current query
        context_parts.append(f"\nCustomer: {req.message}")
        context_parts.append("\nAssistant:")
        
        # Combine all context with clear separation
        full_prompt = "\n\n".join(context_parts)
        
        # Use consistent temperature
        temperature = 0.7
        
        # Get AI response with improved parameters
        answer = get_mia_response_improved(full_prompt, temperature=temperature, max_tokens=400)
        
        # Save user message
        user_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="client",
            message=req.message
        )
        db.add(user_message)
        
        # Save AI response
        ai_message = models.ChatMessage(
            restaurant_id=req.restaurant_id,
            client_id=req.client_id,
            sender_type="ai",
            message=answer
        )
        db.add(ai_message)
        
        db.commit()
        
        logger.info("MIA response processed successfully (improved version)")
        
    except Exception as e:
        logger.error(f"Error in improved MIA chat service: {e}")
        answer = "I apologize for the technical difficulty. Please try again or ask our staff for assistance."
    
    return ChatResponse(answer=answer)

# Helper functions
def fetch_recent_chat_history(db: Session, client_id: str, restaurant_id: str):
    """Fetch recent chat history for context"""
    logger.info(f"Fetching chat history for client {client_id}, restaurant {restaurant_id}")
    
    # Get messages from last 2 hours for better context
    cutoff_time = datetime.utcnow() - timedelta(hours=2)
    
    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == client_id,
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.timestamp >= cutoff_time,
        models.ChatMessage.sender_type.in_(['client', 'ai'])
    ).order_by(models.ChatMessage.timestamp.asc()).limit(10).all()
    
    logger.info(f"Found {len(recent_messages)} recent messages for context")
    
    return recent_messages

def get_or_create_client(db: Session, client_id: str, restaurant_id: str, phone_number: str = None):
    """Get or create a client record."""
    client = db.query(models.Client).filter_by(id=client_id).first()
    if not client:
        try:
            client = models.Client(
                id=client_id, 
                restaurant_id=restaurant_id,
                phone_number=phone_number
            )
            db.add(client)
            db.commit()
            db.refresh(client)
        except IntegrityError:
            db.rollback()
            client = db.query(models.Client).filter_by(id=client_id).first()
    else:
        # Update phone number if provided and not already set
        if phone_number and not client.phone_number:
            client.phone_number = phone_number
            db.commit()
            db.refresh(client)
    return client

# Optional: Function to analyze and improve prompts over time
def analyze_conversation_success(db: Session, client_id: str, restaurant_id: str):
    """Analyze conversation patterns to improve responses"""
    # This could be used to track which types of responses work best
    # and adjust the system accordingly
    pass