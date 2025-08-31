"""
Main MIA Chat Service Router
Routes to appropriate service based on business RAG mode
"""
import logging
from sqlalchemy.orm import Session
import models
from schemas.chat import ChatRequest, ChatResponse

logger = logging.getLogger(__name__)

def get_or_create_client(db: Session, client_id: str, restaurant_id: str):
    """Get or create a client"""
    client = db.query(models.Client).filter_by(
        id=client_id,
        restaurant_id=restaurant_id
    ).first()
    
    if not client:
        client = models.Client(
            id=client_id,
            restaurant_id=restaurant_id,
            device_info={}
        )
        db.add(client)
        db.commit()
        db.refresh(client)
    
    return client

def mia_chat_service(req: ChatRequest, db: Session) -> ChatResponse:
    """Main router for MIA chat services based on RAG mode"""
    
    # Get business configuration
    business = db.query(models.Business).filter(
        models.Business.business_id == req.restaurant_id
    ).first()
    
    if not business:
        # Try restaurant table for backward compatibility
        restaurant = db.query(models.Restaurant).filter(
            models.Restaurant.restaurant_id == req.restaurant_id
        ).first()
        
        if restaurant:
            # Use restaurant's rag_mode or default
            rag_mode = getattr(restaurant, 'rag_mode', 'full_menu')
        else:
            return ChatResponse(answer="Business not found")
    else:
        rag_mode = business.rag_mode or 'full_menu'
    
    logger.info(f"Using RAG mode: {rag_mode} for {req.restaurant_id}")
    
    # Route to appropriate service
    if rag_mode == "full_menu":
        from services.mia_chat_service_full_menu import mia_chat_service_full_menu
        return mia_chat_service_full_menu(req, db)
        
    elif rag_mode == "full_menu_compact":
        # New compact full menu with tool calling
        from services.mia_chat_service_full_menu_compact import mia_chat_service_full_menu_compact
        return mia_chat_service_full_menu_compact(req, db)
        
    elif rag_mode == "smart_menu":
        from services.mia_chat_service_smart_menu import mia_chat_service_smart_menu
        return mia_chat_service_smart_menu(req, db)
        
    elif rag_mode == "db_query":
        from services.mia_chat_service_db_query import mia_chat_service_db_query
        return mia_chat_service_db_query(req, db)
        
    elif rag_mode == "hybrid":
        from services.mia_chat_service_hybrid import mia_chat_service_hybrid
        return mia_chat_service_hybrid(req, db)
        
    elif rag_mode == "enhanced":
        from services.mia_chat_service_enhanced import mia_chat_service_enhanced
        return mia_chat_service_enhanced(req, db)
        
    else:
        # Default to full menu
        logger.warning(f"Unknown RAG mode '{rag_mode}', defaulting to full_menu")
        from services.mia_chat_service_full_menu import mia_chat_service_full_menu
        return mia_chat_service_full_menu(req, db)