"""
Debug endpoints to help troubleshoot deployment issues
"""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from database import get_db
from pydantic import BaseModel

router = APIRouter(tags=["debug"])

@router.get("/debug/health")
def debug_health():
    """Simple health check that should always work"""
    return {"status": "ok", "message": "Debug endpoint working"}

@router.get("/debug/imports")
def debug_imports():
    """Test if imports are working"""
    try:
        import models
        models_ok = True
    except Exception as e:
        models_ok = str(e)
    
    try:
        from services.mia_chat_service import mia_chat_service
        mia_service_ok = True
    except Exception as e:
        mia_service_ok = str(e)
    
    try:
        from config import get_chat_provider_info
        config_ok = True
    except Exception as e:
        config_ok = str(e)
    
    return {
        "models": models_ok,
        "mia_service": mia_service_ok,
        "config": config_ok
    }

@router.get("/debug/chat-provider")
def get_chat_provider():
    """Get current chat provider information"""
    from config import get_chat_provider_info
    return get_chat_provider_info()

@router.get("/debug/code-version")
def get_code_version():
    """Check which version of code is running"""
    import os
    import subprocess
    
    # Check if mia_chat_service has our fixes
    mia_path = os.path.join(os.path.dirname(__file__), "..", "services", "mia_chat_service.py")
    has_v3_fixes = False
    system_prompt_preview = "Unknown"
    
    try:
        with open(mia_path, 'r') as f:
            content = f.read()
            has_v3_fixes = "v3-291e0cc" in content or "ABSOLUTE REQUIREMENT" in content
            
            # Extract system prompt preview
            if "system_prompt = " in content:
                start = content.find('system_prompt = """') + 19
                end = content.find('"""', start)
                system_prompt_preview = content[start:start+100] + "..."
    except:
        pass
    
    # Git info
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()[:8]
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    except:
        commit = "unknown"
        branch = "unknown"
    
    return {
        "branch": branch,
        "commit": commit,
        "has_v3_fixes": has_v3_fixes,
        "system_prompt_preview": system_prompt_preview,
        "mia_chat_service_exists": os.path.exists(mia_path),
        "deployment_check": "v3-291e0cc"
    }

@router.get("/debug/test-pasta-context/{restaurant_id}")
def test_pasta_context(restaurant_id: str):
    """Test pasta context building directly"""
    from sqlalchemy.orm import Session
    from database import get_db
    import models
    from services.mia_chat_service import format_menu_for_context
    
    db = next(get_db())
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        return {"error": "Restaurant not found"}
    
    data = restaurant.data or {}
    menu_items = data.get("menu", [])
    
    # Build context for pasta query
    pasta_context = format_menu_for_context(menu_items, "what pasta do you have")
    
    # Also manually check pasta items
    pasta_found = []
    for i, item in enumerate(menu_items):
        name = item.get('name') or item.get('dish', '')
        if any(p in name.lower() for p in ['pasta', 'spaghetti', 'linguine', 'penne', 'ravioli', 'lasagna', 'gnocchi']):
            pasta_found.append(f"{i}: {name}")
    
    return {
        "total_menu_items": len(menu_items),
        "pasta_context": pasta_context,
        "pasta_items_found": len(pasta_found),
        "pasta_items": pasta_found[:10],
        "first_10_items": [f"{i}: {item.get('name') or item.get('dish', 'NO NAME')}" for i, item in enumerate(menu_items[:10])]
    }


class SearchDebugRequest(BaseModel):
    business_id: str
    query: str


@router.post("/debug/search")
def debug_search(req: SearchDebugRequest, db: Session = Depends(get_db)):
    """Debug text search functionality"""
    from services.text_search_service import text_search_service
    from services.embedding_service_universal import universal_embedding_service
    
    # Check if ML is available
    ml_available = universal_embedding_service.model is not None
    
    # Try text search directly
    text_results = text_search_service.search_products(
        db, req.business_id, req.query, limit=5
    )
    
    # Try embedding search
    embedding_results = []
    embedding_error = None
    try:
        embedding_results = universal_embedding_service.search_similar_items(
            db, req.business_id, req.query, limit=5
        )
    except Exception as e:
        embedding_error = str(e)
    
    return {
        "ml_available": ml_available,
        "query": req.query,
        "text_search_results": text_results,
        "embedding_search_results": embedding_results,
        "embedding_error": embedding_error
    }


@router.get("/debug/business/{business_id}/products")
def debug_business_products(business_id: str, db: Session = Depends(get_db)):
    """Check products for a business"""
    from sqlalchemy import text
    
    # Check if business exists
    business_result = db.execute(text("""
        SELECT business_id, business_type, data::text 
        FROM businesses 
        WHERE business_id = :business_id
    """), {"business_id": business_id}).fetchone()
    
    if not business_result:
        return {"error": f"Business '{business_id}' not found"}
    
    # Get products
    products_result = db.execute(text("""
        SELECT id, name, price, description, category, product_type, tags::text 
        FROM products 
        WHERE business_id = :business_id
        ORDER BY price
    """), {"business_id": business_id}).fetchall()
    
    products = []
    for p in products_result:
        products.append({
            "id": p[0],
            "name": p[1],
            "price": p[2],
            "description": p[3][:100] + "..." if p[3] and len(p[3]) > 100 else p[3],
            "category": p[4],
            "product_type": p[5],
            "tags": p[6]
        })
    
    return {
        "business": {
            "id": business_result[0],
            "type": business_result[1],
            "data": business_result[2][:200] + "..." if business_result[2] and len(business_result[2]) > 200 else business_result[2]
        },
        "products_count": len(products),
        "products": products
    }


@router.post("/debug/test-placeholder-removal")
def test_placeholder_removal():
    """Test placeholder removal service"""
    from services.placeholder_remover import placeholder_remover
    
    test_cases = [
        "Hello [Customer's Name], I'm glad to help you.",
        "Hi [Customer Name], welcome to [Business Name]!",
        "Dear [Customer's Name], I'm [Your Name] and I'll assist you.",
        "[Customer's Name], thank you for your inquiry.",
        "Hello! I'm happy to help you today.",  # Should not change
    ]
    
    results = []
    for test in test_cases:
        cleaned = placeholder_remover.remove_placeholders(test)
        valid = placeholder_remover.validate_response(cleaned)
        results.append({
            "original": test,
            "cleaned": cleaned,
            "is_valid": valid
        })
    
    # Test with customer name
    with_name = placeholder_remover.clean_response(
        "Hello [Customer's Name], how can I help?", 
        customer_name="John"
    )
    
    return {
        "test_results": results,
        "with_customer_name": {
            "original": "Hello [Customer's Name], how can I help?",
            "cleaned": with_name
        }
    }