"""
MIA Chat Service - Simplified version that works
"""
import requests
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
MIA_LOCAL_URL = os.getenv("MIA_LOCAL_URL", "http://localhost:8001")

# System prompt
system_prompt = """
You are a friendly restaurant assistant helping customers with menu questions.

ABSOLUTE REQUIREMENT: When asked about any food category (pasta, pizza, salad, etc.), you MUST list EVERY SINGLE item from that category shown in the context below. Do not select "examples" or "some options" - list them ALL.

RULES:
1. "What pasta do you have" = List ALL pasta items, exactly as shown in context
2. "What are your pasta options" = List ALL pasta items, exactly as shown in context  
3. Never say "including" or "such as" - these imply there are more options not listed
4. Format: "We have [complete list of ALL items]" or "Our pasta dishes are [complete list]"
5. Treat these as equivalent: "what X do you have", "X options", "X choices", "X dishes"
6. Always respond in the same language as the customer's message

The context below contains the COMPLETE list. Your job is to relay it fully, not summarize.
"""

def get_mia_response_direct(prompt: str, max_tokens: int = 150) -> str:
    """Get response from MIA using direct API endpoint"""
    try:
        # First try local MIA instance
        try:
            response = requests.post(
                f"{MIA_LOCAL_URL}/generate",
                json={
                    "prompt": prompt,
                    "max_tokens": max_tokens,
                    "temperature": 0.7,
                    "restaurant_mode": True
                },
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("text", "I'm having trouble understanding. Could you please rephrase?")
        except:
            logger.info("Local MIA not available, trying remote")
        
        # Try remote MIA backend
        response = requests.post(
            f"{MIA_BACKEND_URL}/api/generate",
            json={
                "prompt": prompt,
                "max_tokens": max_tokens,
                "temperature": 0.7,
                "source": "restaurant"
            },
            headers={
                "Content-Type": "application/json",
                "X-Source": "restaurant-backend"
            },
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result.get("text", result.get("response", "I'm having trouble understanding. Could you please rephrase?"))
        else:
            logger.error(f"MIA API error: {response.status_code} - {response.text}")
            return "I apologize, but I'm having technical difficulties. Please try again in a moment or ask our staff for assistance."
            
    except requests.exceptions.Timeout:
        logger.error("MIA request timed out")
        return "I'm taking a bit longer to respond. Please try again."
    except Exception as e:
        logger.error(f"Error getting MIA response: {e}")
        return "I'm experiencing technical difficulties. Please try again or ask our staff for help."

def fetch_recent_chat_history(db: Session, client_id: str, restaurant_id: str):
    """Fetch recent chat history for context"""
    logger.info(f"Fetching chat history for client {client_id}, restaurant {restaurant_id}")
    
    cutoff_time = datetime.utcnow() - timedelta(minutes=60)
    
    recent_messages = db.query(models.ChatMessage).filter(
        models.ChatMessage.client_id == client_id,
        models.ChatMessage.restaurant_id == restaurant_id,
        models.ChatMessage.timestamp >= cutoff_time,
        models.ChatMessage.sender_type.in_(['client', 'ai'])
    ).order_by(models.ChatMessage.timestamp.asc()).limit(20).all()
    
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
        if phone_number and not client.phone_number:
            client.phone_number = phone_number
            db.commit()
            db.refresh(client)
    return client

def format_menu_for_context(menu_items, query):
    """Format menu items for context - improved version"""
    if not menu_items:
        return "Menu data unavailable."
    
    # Log total menu items for debugging
    logger.info(f"format_menu_for_context: Total menu items: {len(menu_items)}")
    
    query_lower = query.lower()
    context_lines = []
    
    # For general menu queries, show categories
    if any(word in query_lower for word in ['menu', 'serve', 'offer', 'have', 'dishes']):
        categories = {}
        for item in menu_items[:30]:  # Limit for performance
            cat = item.get('subcategory', 'main')
            if cat not in categories:
                categories[cat] = []
            name = item.get('name') or item.get('dish', '')
            if name:
                categories[cat].append(name)
        
        for cat, items in categories.items():
            if items:
                context_lines.append(f"{cat.title()}: {', '.join(items[:5])}")
    
    # For specific queries, find relevant items
    else:
        found_items = []
        
        # Log search details for debugging
        if 'pasta' in query_lower:
            logger.info(f"Searching for pasta in {len(menu_items)} menu items")
        
        # Search ALL menu items for relevance - no limit
        for idx, item in enumerate(menu_items):
            name = item.get('name') or item.get('dish', '')
            if not name:
                continue
                
            name_lower = name.lower()
            ingredients = item.get('ingredients', [])
            description = item.get('description', '').lower()
            
            # Check relevance - improved matching
            relevant = False
            
            # Special handling for dietary queries
            if 'vegetarian' in query_lower or 'vegan' in query_lower:
                meat_keywords = ['beef', 'pork', 'chicken', 'duck', 'lamb', 'veal', 'bacon', 'guanciale']
                if not any(meat in str(ingredients).lower() for meat in meat_keywords):
                    relevant = True
            # Special handling for pasta queries
            elif 'pasta' in query_lower:
                pasta_keywords = ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi', 'fettuccine', 'rigatoni', 'tagliatelle']
                # Check name, description AND ingredients for pasta keywords
                item_text = f"{name_lower} {description} {' '.join(str(i).lower() for i in ingredients)}"
                if any(keyword in item_text for keyword in pasta_keywords):
                    relevant = True
                    if 'pasta' in query_lower:
                        logger.info(f"  Found pasta item at index {idx}: {name}")
            # Check if query words appear in name, description, or ingredients
            else:
                query_words = [w for w in query_lower.split() if len(w) > 2]  # Changed from > 3
                for word in query_words:
                    if (word in name_lower or 
                        word in description or
                        any(word in ing.lower() for ing in ingredients)):
                        relevant = True
                        break
            
            if relevant:
                price = item.get('price', '')
                desc = item.get('description', '')[:80]  # Show more description
                found_items.append({
                    'name': name,
                    'price': price,
                    'desc': desc,
                    'category': item.get('subcategory', 'main')
                })
        
        # Log findings for pasta queries
        if 'pasta' in query_lower:
            logger.info(f"Found {len(found_items)} pasta items from search")
            # Log what was found
            for item in found_items[:10]:
                logger.info(f"  - {item['name']}")
        
        # Format found items
        if found_items:
            # For pasta queries and similar, show all items without too much detail
            if 'pasta' in query_lower or len(found_items) > 5:
                # Group by category
                by_category = {}
                # For pasta, show ALL items, not limited
                limit = None if 'pasta' in query_lower else 15
                items_to_show = found_items if limit is None else found_items[:limit]
                for item in items_to_show:
                    cat = item['category']
                    if cat not in by_category:
                        by_category[cat] = []
                    by_category[cat].append(f"{item['name']} ({item['price']})")
                
                for cat, items in by_category.items():
                    context_lines.append(f"{cat.title()}: {', '.join(items)}")
            else:
                # Show detailed info for few items
                for item in found_items[:5]:
                    context_lines.append(f"{item['name']} ({item['price']}): {item['desc']}")
        
        # If nothing found, provide helpful context
        if not context_lines:
            # Special fallback for pasta - ensure we always find pasta dishes
            if 'pasta' in query_lower:
                logger.warning("No pasta found in regular search, trying fallback")
                pasta_dishes = []
                for item in menu_items:
                    name = item.get('name', '').lower()
                    if any(p in name for p in ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']):
                        pasta_dishes.append(f"{item.get('name')} ({item.get('price', '')})")
                if pasta_dishes:
                    context_lines.append(f"Pasta dishes: {', '.join(pasta_dishes)}")
                else:
                    context_lines.append("I couldn't find pasta dishes in our menu.")
            else:
                context_lines.append("I couldn't find specific items matching your query in our menu.")
    
    return "\n".join(context_lines) if context_lines else ""

def mia_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Handle chat requests using MIA backend - simplified version"""
    
    logger.info(f"MIA CHAT SERVICE - Restaurant: {req.restaurant_id}, Client: {req.client_id}")
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if not restaurant:
        logger.error(f"Restaurant not found: {req.restaurant_id}")
        return ChatResponse(answer="I'm sorry, I cannot find information about this restaurant.")
    
    # Check if this is a restaurant staff message
    if req.sender_type == 'restaurant':
        logger.info("Blocking AI response for restaurant staff message")
        return ChatResponse(answer="")
    
    # Get restaurant data
    data = restaurant.data or {}
    
    try:
        # Get menu items
        menu_items = data.get("menu", [])
        if menu_items:
            try:
                menu_items = apply_menu_fallbacks(menu_items)
            except Exception as e:
                logger.warning(f"Error applying menu fallbacks: {e}")
        
        # Build context
        context_parts = [system_prompt]
        context_parts.append(f"\nRestaurant: {restaurant.restaurant_id}")
        context_parts.append(f"Customer asks: '{req.message}'")
        
        # Add menu context
        menu_context = format_menu_for_context(menu_items, req.message)
        if menu_context:
            context_parts.append("\nRelevant menu information:")
            context_parts.append(menu_context)
            
        # Log context for pasta queries
        if 'pasta' in req.message.lower():
            logger.info(f"PASTA QUERY - Context built: {menu_context}")
        
        # Add opening hours if asked
        if any(word in req.message.lower() for word in ['hour', 'open', 'close', 'when']):
            hours = data.get('opening_hours', {})
            if hours:
                context_parts.append(f"\nOpening hours: {hours}")
        
        # Final prompt
        full_prompt = "\n".join(context_parts)
        
        # Add explicit instruction for category queries
        if any(cat in req.message.lower() for cat in ['pasta', 'pizza', 'salad', 'dessert', 'wine', 'appetizer']):
            full_prompt += "\n\nREMINDER: List ALL items from the context above - do not truncate or select just a few."
        
        full_prompt += f"\n\nCustomer: {req.message}\nAssistant:"
        
        # Get response from MIA - increased tokens for complete lists
        answer = get_mia_response_direct(full_prompt, max_tokens=250)
        
        # Log if pasta query truncated
        if 'pasta' in req.message.lower() and answer:
            pasta_count = sum(1 for p in ['Spaghetti', 'Ravioli', 'Penne', 'Linguine', 'Gnocchi', 'Lasagna'] if p in answer)
            logger.info(f"PASTA QUERY - Response mentions {pasta_count} pasta dishes")
        
    except Exception as e:
        logger.error(f"Error in MIA chat service: {e}")
        answer = "I'm experiencing technical difficulties. Please try again later."
    
    # Save AI response
    new_message = models.ChatMessage(
        restaurant_id=req.restaurant_id,
        client_id=req.client_id,
        sender_type="ai",
        message=answer
    )
    db.add(new_message)
    db.commit()
    
    logger.info("MIA response processed successfully")
    
    return ChatResponse(answer=answer)