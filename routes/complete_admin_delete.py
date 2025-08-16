"""
Complete admin deletion endpoint that handles ALL foreign keys
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from auth import get_current_owner
import models
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/complete-admin", tags=["complete-admin"])

@router.delete("/force-delete/{restaurant_id}")
def force_delete_restaurant(
    restaurant_id: str,
    current_admin: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """
    Force delete a restaurant and ALL related data.
    Handles all foreign key constraints in the correct order.
    """
    # Check if admin
    if current_admin.restaurant_id != "admin@admin.com":
        raise HTTPException(status_code=403, detail="Admin only")
    
    # Don't delete self
    if restaurant_id == "admin@admin.com":
        raise HTTPException(status_code=400, detail="Cannot delete admin")
    
    try:
        # Start transaction
        logger.info(f"Starting complete deletion of restaurant {restaurant_id}")
        
        # Delete in the correct order to avoid foreign key violations
        
        # 1. Delete menu_embeddings (no dependencies)
        del1 = db.execute(text("DELETE FROM menu_embeddings WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        logger.info(f"Deleted {del1.rowcount} menu embeddings")
        
        # 2. Delete chat_logs (depends on restaurant_id and client_id)
        # First by restaurant_id
        del2a = db.execute(text("DELETE FROM chat_logs WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        # Then by client_id
        del2b = db.execute(text("""
            DELETE FROM chat_logs 
            WHERE client_id IN (
                SELECT id FROM clients WHERE restaurant_id = :rid
            )
        """), {"rid": restaurant_id})
        logger.info(f"Deleted {del2a.rowcount + del2b.rowcount} chat logs")
        
        # 3. Delete chat_messages (depends on restaurant_id and client_id)
        # First delete by client_id to avoid foreign key issues
        del3a = db.execute(text("""
            DELETE FROM chat_messages 
            WHERE client_id IN (
                SELECT id FROM clients WHERE restaurant_id = :rid
            )
        """), {"rid": restaurant_id})
        # Then by restaurant_id
        del3b = db.execute(text("DELETE FROM chat_messages WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        logger.info(f"Deleted {del3a.rowcount + del3b.rowcount} chat messages")
        
        # 4. Now we can safely delete clients
        del4 = db.execute(text("DELETE FROM clients WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        logger.info(f"Deleted {del4.rowcount} clients")
        
        # 5. Finally delete the restaurant
        del5 = db.execute(text("DELETE FROM restaurants WHERE restaurant_id = :rid"), {"rid": restaurant_id})
        logger.info(f"Deleted restaurant record")
        
        # Commit the transaction
        db.commit()
        
        return {
            "success": True,
            "message": f"Successfully deleted {restaurant_id} and all related data",
            "deleted": {
                "embeddings": del1.rowcount,
                "chat_logs": del2a.rowcount + del2b.rowcount,
                "messages": del3a.rowcount + del3b.rowcount,
                "clients": del4.rowcount,
                "restaurant": del5.rowcount
            }
        }
        
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to delete {restaurant_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))