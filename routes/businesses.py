"""
Business discovery and listing endpoints
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import get_db
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/businesses", tags=["businesses"])

class BusinessInfo(BaseModel):
    business_id: str
    name: str
    type: str
    description: Optional[str]
    logo_url: Optional[str]
    theme_color: Optional[str]
    
class BusinessListResponse(BaseModel):
    businesses: List[BusinessInfo]
    total: int

@router.get("", response_model=BusinessListResponse)
def list_businesses(
    business_type: Optional[str] = Query(None, description="Filter by business type"),
    search: Optional[str] = Query(None, description="Search in name/description"),
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """List all businesses with optional filtering"""
    
    # Build query
    query = """
        SELECT business_id, data, business_type, metadata
        FROM businesses
        WHERE 1=1
    """
    params = {}
    
    if business_type:
        query += " AND business_type = :business_type"
        params["business_type"] = business_type
        
    if search:
        query += " AND (data->>'name' ILIKE :search OR data->>'description' ILIKE :search)"
        params["search"] = f"%{search}%"
        
    # Count total
    count_query = f"SELECT COUNT(*) FROM ({query}) as filtered"
    total = db.execute(text(count_query), params).scalar()
    
    # Add pagination
    query += " ORDER BY data->>'name' LIMIT :limit OFFSET :skip"
    params["limit"] = limit
    params["skip"] = skip
    
    # Execute query
    results = db.execute(text(query), params).fetchall()
    
    # Format results
    businesses = []
    for row in results:
        business_id, data, business_type, metadata = row
        businesses.append(BusinessInfo(
            business_id=business_id,
            name=data.get("name", business_id),
            type=business_type,
            description=data.get("description"),
            logo_url=metadata.get("logo_url") if metadata else None,
            theme_color=metadata.get("theme_color") if metadata else None
        ))
    
    return BusinessListResponse(businesses=businesses, total=total)

@router.get("/types")
def get_business_types(db: Session = Depends(get_db)):
    """Get all available business types"""
    query = text("""
        SELECT DISTINCT business_type, COUNT(*) as count
        FROM businesses
        GROUP BY business_type
        ORDER BY count DESC
    """)
    
    results = db.execute(query).fetchall()
    
    return {
        "types": [
            {"type": row[0], "count": row[1]} 
            for row in results
        ]
    }

@router.get("/{business_id}")
def get_business_details(business_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific business"""
    query = text("""
        SELECT business_id, data, business_type, metadata,
               (SELECT COUNT(*) FROM products WHERE business_id = b.business_id) as product_count
        FROM businesses b
        WHERE business_id = :business_id
    """)
    
    result = db.execute(query, {"business_id": business_id}).fetchone()
    
    if not result:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Business not found")
    
    business_id, data, business_type, metadata, product_count = result
    
    return {
        "business_id": business_id,
        "name": data.get("name", business_id),
        "type": business_type,
        "description": data.get("description"),
        "contact": {
            "email": data.get("email"),
            "phone": data.get("phone"),
            "address": data.get("address"),
            "website": data.get("website")
        },
        "metadata": metadata,
        "product_count": product_count,
        "chat_enabled": True,
        "theme": {
            "primary_color": metadata.get("theme_color", "#1976d2") if metadata else "#1976d2",
            "logo_url": metadata.get("logo_url") if metadata else None,
            "chat_widget_position": metadata.get("chat_position", "bottom-right") if metadata else "bottom-right"
        }
    }