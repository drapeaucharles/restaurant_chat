"""
API routes for menu validation statistics
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from database import get_db
from auth import verify_restaurant_token
from services.menu_validation_logger import menu_validation_logger
from typing import Optional

router = APIRouter()

@router.get("/validation-stats/{restaurant_id}")
def get_validation_stats(
    restaurant_id: str,
    restaurant: dict = Depends(verify_restaurant_token),
    db: Session = Depends(get_db)
):
    """Get menu validation error statistics for a restaurant"""
    
    # Verify the restaurant has access to these stats
    if restaurant["restaurant_id"] != restaurant_id and restaurant.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Access denied to validation stats")
    
    # Get statistics
    stats = menu_validation_logger.get_error_statistics(restaurant_id)
    
    # Get recent errors
    recent_errors = menu_validation_logger.get_recent_errors(restaurant_id, limit=10)
    
    return {
        "restaurant_id": restaurant_id,
        "statistics": stats,
        "recent_errors": recent_errors,
        "message": "Menu validation statistics retrieved successfully"
    }

@router.get("/validation-stats")
def get_all_validation_stats(
    restaurant: dict = Depends(verify_restaurant_token),
    db: Session = Depends(get_db)
):
    """Get overall menu validation error statistics (admin only)"""
    
    # Only allow admin access
    if restaurant.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    # Get overall statistics
    stats = menu_validation_logger.get_error_statistics()
    
    # Get recent errors across all restaurants
    recent_errors = menu_validation_logger.get_recent_errors(limit=20)
    
    return {
        "statistics": stats,
        "recent_errors": recent_errors,
        "message": "Overall menu validation statistics retrieved successfully"
    }