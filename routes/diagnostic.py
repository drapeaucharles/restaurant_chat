"""
Comprehensive diagnostic endpoint for memory services
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from schemas.chat import ChatRequest
import logging
import traceback
import json
from services.redis_helper import redis_client
from services.mia_chat_service_hybrid import HybridQueryClassifier

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/diagnostic/memory")
async def diagnose_memory_service(req: ChatRequest, db: Session = Depends(get_db)):
    """Comprehensive diagnostic for memory services"""
    
    results = {
        "request": {
            "restaurant_id": req.restaurant_id,
            "client_id": req.client_id,
            "message": req.message,
            "sender_type": req.sender_type
        },
        "redis": {},
        "memory_services": {},
        "components": {},
        "errors": []
    }
    
    # Test 1: Redis connectivity
    try:
        # Test Redis
        test_key = "diagnostic_test"
        redis_client.setex(test_key, 60, "test_value")
        retrieved = redis_client.get(test_key)
        results["redis"] = {
            "connected": redis_client._redis_available,
            "test_write": "success",
            "test_read": retrieved == "test_value"
        }
    except Exception as e:
        results["redis"] = {
            "connected": False,
            "error": str(e)
        }
    
    # Test 2: Memory service loading
    try:
        # Test each memory service
        services_to_test = [
            ("memory_working", "services.rag_chat_memory_working", "working_memory_rag"),
            ("memory_best", "services.rag_chat_memory_best", "best_memory_rag"),
            ("enhanced_v3_lazy", "services.rag_chat_enhanced_v3_lazy", "enhanced_rag_chat_v3")
        ]
        
        for service_name, module_path, instance_name in services_to_test:
            try:
                module = __import__(module_path, fromlist=[instance_name])
                service = getattr(module, instance_name)
                results["memory_services"][service_name] = {
                    "loaded": True,
                    "has_get_memory": hasattr(service, 'get_memory') if hasattr(service, '__dict__') else "N/A"
                }
            except Exception as e:
                results["memory_services"][service_name] = {
                    "loaded": False,
                    "error": str(e),
                    "traceback": traceback.format_exc()
                }
    except Exception as e:
        results["errors"].append(f"Service loading test failed: {str(e)}")
    
    # Test 3: Component testing
    try:
        # Test query classifier
        query_type = HybridQueryClassifier.classify(req.message)
        results["components"]["query_classifier"] = {
            "success": True,
            "query_type": query_type.value
        }
    except Exception as e:
        results["components"]["query_classifier"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 4: Test embedding service
    try:
        from services.embedding_service import embedding_service
        test_items = embedding_service.search_similar_items(
            db=db,
            restaurant_id=req.restaurant_id,
            query=req.message,
            limit=5,
            threshold=0.35
        )
        results["components"]["embedding_service"] = {
            "success": True,
            "items_found": len(test_items) if test_items else 0
        }
    except Exception as e:
        results["components"]["embedding_service"] = {
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }
    
    # Test 5: Test allergen service
    try:
        from services.allergen_service import allergen_service
        allergen_data = allergen_service.get_items_for_restriction(
            db, req.restaurant_id, "vegetarian"
        )
        results["components"]["allergen_service"] = {
            "success": True,
            "safe_items": len(allergen_data.get('safe_items', []))
        }
    except Exception as e:
        results["components"]["allergen_service"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 6: Test context formatter
    try:
        from services.context_formatter import context_formatter, ContextSection
        test_sections = {
            ContextSection.PERSONALIZATION: "Test personalization",
            ContextSection.MENU_ITEMS: "Test menu items"
        }
        formatted = context_formatter.format_context(test_sections)
        results["components"]["context_formatter"] = {
            "success": True,
            "formatted_length": len(formatted)
        }
    except Exception as e:
        results["components"]["context_formatter"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 7: Test response validator
    try:
        from services.response_validator import response_validator
        test_response = "Here are some items: Pasta ($12), Pizza ($15)"
        validated = response_validator.validate_and_correct(test_response, db, req.restaurant_id)
        results["components"]["response_validator"] = {
            "success": True,
            "validation_changed": validated != test_response
        }
    except Exception as e:
        results["components"]["response_validator"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 8: Memory storage and retrieval for memory_best
    if results["memory_services"].get("memory_best", {}).get("loaded"):
        try:
            from services.rag_chat_memory_best import best_memory_rag
            
            # Test memory operations
            test_memory_key = best_memory_rag.get_memory_key(req.restaurant_id, req.client_id)
            
            # Save test memory
            test_memory = {
                'name': 'TestUser',
                'history': [{'query': 'test', 'response': 'test response'}],
                'preferences': ['test_pref'],
                'dietary_restrictions': ['test_diet'],
                'mentioned_items': ['test_item'],
                'topics': ['test_topic']
            }
            
            best_memory_rag.save_memory(req.restaurant_id, req.client_id, test_memory)
            
            # Retrieve memory
            retrieved_memory = best_memory_rag.get_memory(req.restaurant_id, req.client_id)
            
            results["components"]["memory_best_storage"] = {
                "success": True,
                "memory_key": test_memory_key,
                "saved_name": test_memory['name'],
                "retrieved_name": retrieved_memory.get('name'),
                "match": retrieved_memory.get('name') == test_memory['name']
            }
        except Exception as e:
            results["components"]["memory_best_storage"] = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    # Test 9: Full execution test for memory_best
    if results["memory_services"].get("memory_best", {}).get("loaded"):
        try:
            from services.rag_chat_memory_best import best_memory_rag
            from schemas.chat import ChatResponse
            
            # Try to process a simple request
            response = best_memory_rag(req, db)
            
            results["components"]["memory_best_execution"] = {
                "success": True,
                "response_type": type(response).__name__,
                "has_answer": bool(getattr(response, 'answer', None)),
                "answer_length": len(response.answer) if hasattr(response, 'answer') else 0
            }
        except Exception as e:
            results["components"]["memory_best_execution"] = {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
    
    return results

@router.get("/diagnostic/memory-contents/{restaurant_id}/{client_id}")
async def get_memory_contents(restaurant_id: str, client_id: str):
    """Get actual memory contents from all storage locations"""
    
    contents = {}
    
    # Check Redis for different key patterns
    key_patterns = [
        f"memory:{restaurant_id}:{client_id}",
        f"best_memory:{restaurant_id}:{client_id}",
        f"conv:{restaurant_id}:{client_id}",
        f"enhanced:{restaurant_id}:{client_id}"
    ]
    
    for pattern in key_patterns:
        try:
            data = redis_client.get(pattern)
            if data:
                contents[pattern] = json.loads(data)
            else:
                contents[pattern] = None
        except Exception as e:
            contents[pattern] = f"Error: {str(e)}"
    
    # Check local memory stores
    try:
        from services.rag_chat_memory_working import MEMORY_STORE as working_store
        working_key = f"memory:{restaurant_id}:{client_id}"
        contents["working_local_store"] = working_store.get(working_key, "Not found")
    except:
        contents["working_local_store"] = "Import failed"
    
    try:
        from services.rag_chat_memory_best import MEMORY_STORE as best_store
        best_key = f"best_memory:{restaurant_id}:{client_id}"
        contents["best_local_store"] = best_store.get(best_key, "Not found")
    except:
        contents["best_local_store"] = "Import failed"
    
    return contents

@router.get("/diagnostic/execution-log")
async def get_execution_log():
    """Get the last execution log from diagnostic service"""
    try:
        from services.rag_chat_memory_diagnostic import get_diagnostic_info
        return get_diagnostic_info()
    except Exception as e:
        return {"error": str(e)}