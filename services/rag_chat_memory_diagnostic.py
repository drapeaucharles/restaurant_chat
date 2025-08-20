"""
Diagnostic version with detailed step-by-step logging
This will help us understand exactly where memory_best fails
"""
import logging
from typing import Dict, List, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from schemas.chat import ChatRequest, ChatResponse
from services.mia_chat_service_hybrid import (
    HybridQueryClassifier,
    QueryType,
    get_hybrid_parameters,
    get_mia_response_hybrid,
    detect_language,
    get_persona_name
)
from services.embedding_service import embedding_service
from services.response_validator import response_validator
from services.allergen_service import allergen_service
from services.context_formatter import context_formatter, ContextSection
from services.redis_helper import redis_client
import models
import re
import json
from datetime import datetime
import traceback

# Set up detailed logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global memory store as backup
MEMORY_STORE = {}

# Global diagnostic info
DIAGNOSTIC_INFO = {
    "last_execution": {},
    "checkpoints": []
}

def log_checkpoint(checkpoint: str, data: dict = None):
    """Log execution checkpoint"""
    entry = {
        "checkpoint": checkpoint,
        "timestamp": datetime.now().isoformat(),
        "data": data or {}
    }
    DIAGNOSTIC_INFO["checkpoints"].append(entry)
    logger.info(f"CHECKPOINT: {checkpoint} - {json.dumps(data or {})}")

class DiagnosticMemoryRAG:
    """Diagnostic version with extensive logging"""
    
    def __init__(self):
        self.embedding_service = embedding_service
        self.similarity_threshold = 0.35
        self.max_context_items = 10
        log_checkpoint("service_initialized")
        
    def get_memory_key(self, restaurant_id: str, client_id: str) -> str:
        """Get memory key"""
        return f"diagnostic_memory:{restaurant_id}:{client_id}"
    
    def get_memory(self, restaurant_id: str, client_id: str) -> Dict:
        """Get memory with logging"""
        key = self.get_memory_key(restaurant_id, client_id)
        log_checkpoint("get_memory_start", {"key": key})
        
        # Try Redis first
        try:
            data = redis_client.get(key)
            if data:
                memory = json.loads(data)
                log_checkpoint("get_memory_redis_success", {
                    "key": key,
                    "name": memory.get('name'),
                    "history_count": len(memory.get('history', []))
                })
                return memory
            else:
                log_checkpoint("get_memory_redis_empty", {"key": key})
        except Exception as e:
            log_checkpoint("get_memory_redis_error", {"key": key, "error": str(e)})
        
        # Fallback to local memory
        default_memory = {
            'name': None,
            'history': [],
            'preferences': [],
            'dietary_restrictions': [],
            'mentioned_items': [],
            'topics': []
        }
        memory = MEMORY_STORE.get(key, default_memory)
        log_checkpoint("get_memory_local", {
            "key": key,
            "found": key in MEMORY_STORE,
            "name": memory.get('name')
        })
        return memory
    
    def save_memory(self, restaurant_id: str, client_id: str, memory: Dict):
        """Save memory with detailed logging"""
        key = self.get_memory_key(restaurant_id, client_id)
        log_checkpoint("save_memory_start", {
            "key": key,
            "name": memory.get('name'),
            "history_count": len(memory.get('history', []))
        })
        
        # Save to local store first
        MEMORY_STORE[key] = memory
        log_checkpoint("save_memory_local_done", {"key": key})
        
        # Try Redis
        try:
            json_data = json.dumps(memory)
            redis_client.setex(key, 14400, json_data)  # 4 hours
            log_checkpoint("save_memory_redis_success", {
                "key": key,
                "data_size": len(json_data)
            })
        except Exception as e:
            log_checkpoint("save_memory_redis_error", {
                "key": key,
                "error": str(e),
                "traceback": traceback.format_exc()
            })
    
    def extract_and_update_memory(self, memory: Dict, message: str, response: str):
        """Extract with detailed logging"""
        log_checkpoint("extract_memory_start", {
            "message_length": len(message),
            "response_length": len(response),
            "current_name": memory.get('name')
        })
        
        try:
            message_lower = message.lower()
            
            # Extract name
            name_match = re.search(r'my name is (\w+)', message, re.IGNORECASE)
            if name_match:
                memory['name'] = name_match.group(1).capitalize()
                log_checkpoint("extract_memory_name_found", {"name": memory['name']})
            
            # Extract dietary restrictions
            found_dietary = []
            for restriction in ['vegetarian', 'vegan', 'gluten-free', 'dairy-free', 'nut-free']:
                if restriction in message_lower:
                    if restriction not in memory['dietary_restrictions']:
                        memory['dietary_restrictions'].append(restriction)
                        found_dietary.append(restriction)
            
            if found_dietary:
                log_checkpoint("extract_memory_dietary", {"found": found_dietary})
            
            # Track topics
            found_topics = []
            for topic in ['pasta', 'pizza', 'seafood', 'salad', 'dessert', 'wine']:
                if topic in message_lower:
                    if topic not in memory['topics']:
                        memory['topics'].append(topic)
                        found_topics.append(topic)
            
            if found_topics:
                log_checkpoint("extract_memory_topics", {"found": found_topics})
            
            # Add to history
            history_item = {
                'query': message,
                'response': response[:200] if response else "",
                'timestamp': datetime.now().isoformat()
            }
            memory['history'].append(history_item)
            
            # Keep only last 10 exchanges
            memory['history'] = memory['history'][-10:]
            
            log_checkpoint("extract_memory_complete", {
                "name": memory.get('name'),
                "dietary_count": len(memory.get('dietary_restrictions', [])),
                "topics_count": len(memory.get('topics', [])),
                "history_count": len(memory.get('history', []))
            })
            
        except Exception as e:
            log_checkpoint("extract_memory_error", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
        
        return memory
    
    def __call__(self, req: ChatRequest, db: Session) -> ChatResponse:
        """Process with comprehensive logging"""
        
        # Clear previous diagnostic info
        DIAGNOSTIC_INFO["checkpoints"] = []
        DIAGNOSTIC_INFO["last_execution"] = {
            "start_time": datetime.now().isoformat(),
            "request": {
                "restaurant_id": req.restaurant_id,
                "client_id": req.client_id,
                "message": req.message
            }
        }
        
        log_checkpoint("request_start", {
            "restaurant_id": req.restaurant_id,
            "client_id": req.client_id,
            "message_length": len(req.message)
        })
        
        try:
            # Skip AI for restaurant messages
            if req.sender_type == 'restaurant':
                log_checkpoint("skipped_restaurant_message")
                return ChatResponse(answer="")
            
            # Get memory FIRST
            memory = self.get_memory(req.restaurant_id, req.client_id)
            log_checkpoint("memory_retrieved", {
                "has_name": bool(memory.get('name')),
                "history_count": len(memory.get('history', []))
            })
            
            # Pre-extract from current message
            memory = self.extract_and_update_memory(memory, req.message, "")
            log_checkpoint("pre_extraction_done")
            
            # Classify query
            query_type = HybridQueryClassifier.classify(req.message)
            language = detect_language(req.message)
            log_checkpoint("classification_done", {
                "query_type": query_type.value,
                "language": language
            })
            
            # Get restaurant
            restaurant = db.query(models.Restaurant).filter(
                models.Restaurant.restaurant_id == req.restaurant_id
            ).first()
            
            if not restaurant:
                log_checkpoint("restaurant_not_found")
                return ChatResponse(answer="Restaurant not found.")
            
            business_name = restaurant.data.get('name', 'our restaurant') if restaurant.data else 'our restaurant'
            log_checkpoint("restaurant_found", {"name": business_name})
            
            # Build prompt
            persona_name = get_persona_name(language)
            if memory['name']:
                prompt = f"You are {persona_name} for {business_name}. Customer name is {memory['name']}. Use their name. Customer says: {req.message}"
            else:
                prompt = f"You are {persona_name} for {business_name}. Customer says: {req.message}"
            
            log_checkpoint("prompt_built", {
                "prompt_length": len(prompt),
                "has_name": bool(memory['name'])
            })
            
            # Get AI response
            params = get_hybrid_parameters(query_type)
            log_checkpoint("ai_request_start")
            
            answer = get_mia_response_hybrid(prompt, params)
            log_checkpoint("ai_response_received", {
                "answer_length": len(answer)
            })
            
            # Test response validation
            log_checkpoint("validation_start")
            try:
                validated_answer = response_validator.validate_and_correct(answer, db, req.restaurant_id)
                log_checkpoint("validation_success", {
                    "changed": answer != validated_answer
                })
                answer = validated_answer
            except Exception as e:
                log_checkpoint("validation_error", {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
            
            # Update memory with response
            memory = self.extract_and_update_memory(memory, req.message, answer)
            log_checkpoint("post_extraction_done")
            
            # Save memory
            self.save_memory(req.restaurant_id, req.client_id, memory)
            log_checkpoint("memory_saved")
            
            # Verify save
            verify_memory = self.get_memory(req.restaurant_id, req.client_id)
            log_checkpoint("memory_verified", {
                "name_matches": verify_memory.get('name') == memory.get('name'),
                "history_matches": len(verify_memory.get('history', [])) == len(memory.get('history', []))
            })
            
            # Save to database
            try:
                new_message = models.ChatMessage(
                    restaurant_id=req.restaurant_id,
                    client_id=req.client_id,
                    sender_type="ai",
                    message=answer
                )
                db.add(new_message)
                db.commit()
                log_checkpoint("database_saved")
            except Exception as e:
                log_checkpoint("database_error", {
                    "error": str(e),
                    "traceback": traceback.format_exc()
                })
                db.rollback()
            
            log_checkpoint("request_complete")
            
            DIAGNOSTIC_INFO["last_execution"]["end_time"] = datetime.now().isoformat()
            DIAGNOSTIC_INFO["last_execution"]["success"] = True
            
            return ChatResponse(
                answer=answer,
                timestamp=req.message
            )
            
        except Exception as e:
            log_checkpoint("fatal_error", {
                "error": str(e),
                "traceback": traceback.format_exc()
            })
            
            DIAGNOSTIC_INFO["last_execution"]["end_time"] = datetime.now().isoformat()
            DIAGNOSTIC_INFO["last_execution"]["success"] = False
            DIAGNOSTIC_INFO["last_execution"]["error"] = str(e)
            
            return ChatResponse(
                answer="I apologize, but I'm having technical difficulties. Please try again.",
                timestamp=req.message if req else ""
            )

# Create singleton
diagnostic_memory_rag = DiagnosticMemoryRAG()

# Export diagnostic info getter
def get_diagnostic_info():
    """Get the diagnostic information"""
    return DIAGNOSTIC_INFO