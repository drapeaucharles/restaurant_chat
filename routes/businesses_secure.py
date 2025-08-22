"""
Secure business routes with proper permissions and audit logging
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
import json
from datetime import datetime

from database import get_db
from auth import get_current_user
from services.security_service import security_service
from services.placeholder_remover import placeholder_remover

router = APIRouter(prefix="/api/v2/businesses", tags=["businesses_v2"])


@router.get("/")
async def list_businesses(
    request: Request,
    business_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    List businesses that the current user has access to
    """
    try:
        # Get user's accessible businesses
        user_businesses = security_service.get_user_businesses(
            db, current_user["id"], current_user["role"]
        )
        
        # Log audit event
        security_service.log_audit_event(
            db=db,
            event_type="business_list",
            user_id=current_user["id"],
            action="list",
            details={"filter": business_type},
            ip_address=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        # Build query
        conditions = ["business_id = ANY(:business_ids)"]
        params = {"business_ids": user_businesses}
        
        if business_type:
            conditions.append("business_type = :business_type")
            params["business_type"] = business_type
        
        query = text(f"""
            SELECT business_id, name, business_type, email, phone, 
                   address, website, description, data, metadata,
                   opening_hours, created_at, updated_at
            FROM businesses
            WHERE {' AND '.join(conditions)}
            ORDER BY name
        """)
        
        results = db.execute(query, params).fetchall()
        
        businesses = []
        for row in results:
            business_data = {
                "business_id": row[0],
                "name": row[1],
                "business_type": row[2],
                "email": row[3],
                "phone": row[4],
                "address": row[5],
                "website": row[6],
                "description": placeholder_remover.remove_placeholders(row[7]) if row[7] else None,
                "data": row[8],
                "metadata": row[9],
                "opening_hours": row[10],
                "created_at": row[11].isoformat() if row[11] else None,
                "updated_at": row[12].isoformat() if row[12] else None
            }
            
            # Sanitize based on permissions
            is_owner = security_service.check_business_permission(
                db, current_user["id"], current_user["role"], row[0], "write"
            )
            sanitized = security_service.sanitize_business_data(
                business_data, current_user["role"], is_owner
            )
            businesses.append(sanitized)
        
        return {"businesses": businesses, "total": len(businesses)}
        
    except Exception as e:
        logger.error(f"Error listing businesses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{business_id}")
async def get_business(
    business_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get a specific business with permission check
    """
    # Check permission
    if not security_service.check_business_permission(
        db, current_user["id"], current_user["role"], business_id
    ):
        raise HTTPException(status_code=403, detail="No permission to access this business")
    
    # Log audit event
    security_service.log_audit_event(
        db=db,
        event_type="business_view",
        user_id=current_user["id"],
        business_id=business_id,
        resource_type="business",
        resource_id=business_id,
        action="view",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Get business
    query = text("""
        SELECT business_id, name, business_type, email, phone, 
               address, website, description, data, metadata,
               opening_hours, rag_mode, created_at, updated_at
        FROM businesses
        WHERE business_id = :business_id
    """)
    
    result = db.execute(query, {"business_id": business_id}).fetchone()
    
    if not result:
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_data = {
        "business_id": result[0],
        "name": result[1],
        "business_type": result[2],
        "email": result[3],
        "phone": result[4],
        "address": result[5],
        "website": result[6],
        "description": placeholder_remover.remove_placeholders(result[7]) if result[7] else None,
        "data": result[8],
        "metadata": result[9],
        "opening_hours": result[10],
        "rag_mode": result[11],
        "created_at": result[12].isoformat() if result[12] else None,
        "updated_at": result[13].isoformat() if result[13] else None
    }
    
    # Sanitize based on permissions
    is_owner = security_service.check_business_permission(
        db, current_user["id"], current_user["role"], business_id, "write"
    )
    
    return security_service.sanitize_business_data(
        business_data, current_user["role"], is_owner
    )


@router.put("/{business_id}")
async def update_business(
    business_id: str,
    update_data: Dict[str, Any],
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Update a business with permission check
    """
    # Validate permissions and update data
    security_service.validate_business_update(
        db, current_user["id"], current_user["role"], business_id, update_data
    )
    
    # Log audit event
    security_service.log_audit_event(
        db=db,
        event_type="business_update",
        user_id=current_user["id"],
        business_id=business_id,
        resource_type="business",
        resource_id=business_id,
        action="update",
        details={"fields": list(update_data.keys())},
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Build update query
    update_fields = []
    params = {"business_id": business_id}
    
    allowed_fields = [
        "name", "email", "phone", "address", "website", 
        "description", "data", "metadata", "opening_hours"
    ]
    
    for field in allowed_fields:
        if field in update_data:
            update_fields.append(f"{field} = :{field}")
            if field in ["data", "metadata", "opening_hours"]:
                params[field] = json.dumps(update_data[field])
            else:
                params[field] = update_data[field]
    
    if not update_fields:
        raise HTTPException(status_code=400, detail="No valid fields to update")
    
    update_fields.append("updated_at = CURRENT_TIMESTAMP")
    
    query = text(f"""
        UPDATE businesses 
        SET {', '.join(update_fields)}
        WHERE business_id = :business_id
        RETURNING business_id
    """)
    
    result = db.execute(query, params).fetchone()
    db.commit()
    
    if not result:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # If products were included, update them
    if "products" in update_data:
        # Delete existing products
        delete_query = text("DELETE FROM products WHERE business_id = :business_id")
        db.execute(delete_query, {"business_id": business_id})
        
        # Insert new products
        for product in update_data["products"]:
            insert_query = text("""
                INSERT INTO products (
                    business_id, name, description, category, 
                    price, metadata, available
                ) VALUES (
                    :business_id, :name, :description, :category,
                    :price, :metadata, :available
                )
            """)
            
            db.execute(insert_query, {
                "business_id": business_id,
                "name": product.get("name"),
                "description": product.get("description"),
                "category": product.get("category"),
                "price": product.get("price"),
                "metadata": json.dumps(product.get("metadata", {})),
                "available": product.get("available", True)
            })
        
        db.commit()
        
        # Re-index for embeddings
        try:
            from routes.embeddings import sync_business_embeddings
            sync_business_embeddings(business_id, db)
        except:
            pass
    
    return {"message": "Business updated successfully", "business_id": business_id}


@router.delete("/{business_id}")
async def delete_business(
    business_id: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Delete a business (admin only)
    """
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Only admins can delete businesses")
    
    # Check if business exists
    check_query = text("SELECT 1 FROM businesses WHERE business_id = :business_id")
    exists = db.execute(check_query, {"business_id": business_id}).fetchone()
    
    if not exists:
        raise HTTPException(status_code=404, detail="Business not found")
    
    # Log audit event
    security_service.log_audit_event(
        db=db,
        event_type="business_delete",
        user_id=current_user["id"],
        business_id=business_id,
        resource_type="business",
        resource_id=business_id,
        action="delete",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Delete related data
    db.execute(text("DELETE FROM products WHERE business_id = :business_id"), 
               {"business_id": business_id})
    db.execute(text("DELETE FROM embeddings WHERE business_id = :business_id"), 
               {"business_id": business_id})
    db.execute(text("DELETE FROM chat_messages WHERE restaurant_id = :business_id"), 
               {"business_id": business_id})
    
    # Delete business
    db.execute(text("DELETE FROM businesses WHERE business_id = :business_id"), 
               {"business_id": business_id})
    
    db.commit()
    
    return {"message": "Business deleted successfully"}


@router.get("/{business_id}/audit-logs")
async def get_business_audit_logs(
    business_id: str,
    request: Request,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user)
):
    """
    Get audit logs for a business (owner or admin only)
    """
    # Check permission
    if current_user["role"] != "admin":
        if not security_service.check_business_permission(
            db, current_user["id"], current_user["role"], business_id, "write"
        ):
            raise HTTPException(status_code=403, detail="No permission to view audit logs")
    
    logs = security_service.get_audit_logs(
        db=db,
        business_id=business_id,
        limit=limit
    )
    
    return {"logs": logs, "total": len(logs)}


@router.get("/public/list")
async def list_public_businesses(
    business_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List businesses publicly (no auth required)
    """
    conditions = []
    params = {}
    
    if business_type:
        conditions.append("business_type = :business_type")
        params["business_type"] = business_type
    
    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    
    query = text(f"""
        SELECT business_id, name, business_type, phone, 
               address, website, description, opening_hours
        FROM businesses
        {where_clause}
        ORDER BY name
    """)
    
    results = db.execute(query, params).fetchall()
    
    businesses = []
    for row in results:
        business = {
            "business_id": row[0],
            "name": row[1],
            "business_type": row[2],
            "phone": row[3],
            "address": row[4],
            "website": row[5],
            "description": placeholder_remover.remove_placeholders(row[6]) if row[6] else None,
            "opening_hours": row[7]
        }
        businesses.append(business)
    
    return {"businesses": businesses, "total": len(businesses)}


# Import logger
import logging
logger = logging.getLogger(__name__)