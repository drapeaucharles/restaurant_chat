"""
Security service for business-specific permissions and audit logging
"""

from typing import Optional, List, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime
import uuid
import logging
import json
from fastapi import HTTPException

logger = logging.getLogger(__name__)


class SecurityService:
    """Service for handling business-specific permissions and audit logging"""
    
    @staticmethod
    def check_business_permission(
        db: Session,
        user_id: str,
        user_role: str,
        business_id: str,
        required_permission: str = "read"
    ) -> bool:
        """
        Check if a user has permission to access a business
        
        Permissions:
        - admin: Full access to all businesses
        - owner: Full access to their own business
        - staff: Limited access to their business
        - user: Read-only access to public data
        """
        
        # Admins have full access
        if user_role == "admin":
            return True
        
        # For non-admins, check business ownership/employment
        if user_role in ["owner", "staff"]:
            # Check if user is associated with this business
            
            # First check businesses table
            business_check = text("""
                SELECT 1 FROM businesses 
                WHERE business_id = :business_id 
                AND password = :user_id
            """)
            result = db.execute(business_check, {
                "business_id": business_id,
                "user_id": user_id
            }).fetchone()
            
            if result:
                return True
            
            # Check restaurants table for backward compatibility
            restaurant_check = text("""
                SELECT 1 FROM restaurants 
                WHERE restaurant_id = :business_id 
                AND password = :user_id
            """)
            result = db.execute(restaurant_check, {
                "business_id": business_id,
                "user_id": user_id
            }).fetchone()
            
            if result:
                return True
            
            # Check staff table
            if user_role == "staff":
                staff_check = text("""
                    SELECT 1 FROM staff 
                    WHERE restaurant_id = :business_id 
                    AND staff_id = :user_id::uuid
                """)
                try:
                    result = db.execute(staff_check, {
                        "business_id": business_id,
                        "user_id": user_id
                    }).fetchone()
                    if result:
                        return True
                except:
                    pass
        
        # Default deny
        return False
    
    @staticmethod
    def log_audit_event(
        db: Session,
        event_type: str,
        user_id: str,
        business_id: Optional[str] = None,
        resource_type: str = "business",
        resource_id: Optional[str] = None,
        action: str = "view",
        details: Optional[Dict[str, Any]] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """
        Log an audit event for security and compliance
        """
        try:
            # Create audit_logs table if it doesn't exist
            create_table_query = text("""
                CREATE TABLE IF NOT EXISTS audit_logs (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    event_type VARCHAR(50) NOT NULL,
                    user_id VARCHAR(255) NOT NULL,
                    business_id VARCHAR(255),
                    resource_type VARCHAR(50),
                    resource_id VARCHAR(255),
                    action VARCHAR(50),
                    details JSONB,
                    ip_address VARCHAR(45),
                    user_agent TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                CREATE INDEX IF NOT EXISTS idx_audit_logs_user_id ON audit_logs(user_id);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_business_id ON audit_logs(business_id);
                CREATE INDEX IF NOT EXISTS idx_audit_logs_created_at ON audit_logs(created_at);
            """)
            db.execute(create_table_query)
            db.commit()
            
            # Insert audit log
            insert_query = text("""
                INSERT INTO audit_logs (
                    event_type, user_id, business_id, resource_type, 
                    resource_id, action, details, ip_address, user_agent
                ) VALUES (
                    :event_type, :user_id, :business_id, :resource_type,
                    :resource_id, :action, :details, :ip_address, :user_agent
                )
            """)
            
            db.execute(insert_query, {
                "event_type": event_type,
                "user_id": user_id,
                "business_id": business_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "action": action,
                "details": json.dumps(details) if details else None,
                "ip_address": ip_address,
                "user_agent": user_agent
            })
            db.commit()
            
            logger.info(f"Audit log created: {event_type} by {user_id} on {resource_type}/{resource_id}")
            
        except Exception as e:
            logger.error(f"Failed to create audit log: {str(e)}")
            # Don't fail the main operation if audit logging fails
            db.rollback()
    
    @staticmethod
    def get_user_businesses(db: Session, user_id: str, user_role: str) -> List[str]:
        """
        Get list of business IDs that a user has access to
        """
        if user_role == "admin":
            # Admins can access all businesses
            businesses_query = text("SELECT business_id FROM businesses")
            businesses = db.execute(businesses_query).fetchall()
            
            restaurants_query = text("SELECT restaurant_id FROM restaurants")
            restaurants = db.execute(restaurants_query).fetchall()
            
            business_ids = [b[0] for b in businesses] + [r[0] for r in restaurants]
            return list(set(business_ids))  # Remove duplicates
        
        business_ids = []
        
        # Check owned businesses
        if user_role == "owner":
            businesses_query = text("""
                SELECT business_id FROM businesses WHERE password = :user_id
            """)
            businesses = db.execute(businesses_query, {"user_id": user_id}).fetchall()
            business_ids.extend([b[0] for b in businesses])
            
            restaurants_query = text("""
                SELECT restaurant_id FROM restaurants WHERE password = :user_id
            """)
            restaurants = db.execute(restaurants_query, {"user_id": user_id}).fetchall()
            business_ids.extend([r[0] for r in restaurants])
        
        # Check staff associations
        if user_role == "staff":
            try:
                staff_query = text("""
                    SELECT restaurant_id FROM staff WHERE staff_id = :user_id::uuid
                """)
                staff_businesses = db.execute(staff_query, {"user_id": user_id}).fetchall()
                business_ids.extend([s[0] for s in staff_businesses])
            except:
                pass
        
        return list(set(business_ids))  # Remove duplicates
    
    @staticmethod
    def sanitize_business_data(
        business_data: Dict[str, Any],
        user_role: str,
        is_owner: bool = False
    ) -> Dict[str, Any]:
        """
        Sanitize business data based on user permissions
        """
        # Admin and owners see everything
        if user_role == "admin" or is_owner:
            return business_data
        
        # Staff see limited data
        if user_role == "staff":
            allowed_fields = [
                "business_id", "name", "business_type", "address", 
                "phone", "email", "website", "opening_hours", "description"
            ]
            return {k: v for k, v in business_data.items() if k in allowed_fields}
        
        # Public users see minimal data
        public_fields = [
            "business_id", "name", "business_type", "address", 
            "phone", "website", "opening_hours", "description"
        ]
        return {k: v for k, v in business_data.items() if k in public_fields}
    
    @staticmethod
    def validate_business_update(
        db: Session,
        user_id: str,
        user_role: str,
        business_id: str,
        update_data: Dict[str, Any]
    ) -> bool:
        """
        Validate if a user can update specific fields of a business
        """
        # Check basic permission
        if not SecurityService.check_business_permission(
            db, user_id, user_role, business_id, "write"
        ):
            raise HTTPException(status_code=403, detail="No permission to update this business")
        
        # Admin can update anything
        if user_role == "admin":
            return True
        
        # Restricted fields for non-admins
        restricted_fields = ["business_id", "password", "role", "rag_mode"]
        
        for field in restricted_fields:
            if field in update_data:
                raise HTTPException(
                    status_code=403, 
                    detail=f"No permission to update field: {field}"
                )
        
        return True
    
    @staticmethod
    def get_audit_logs(
        db: Session,
        user_id: Optional[str] = None,
        business_id: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Retrieve audit logs with filters
        """
        query = text("""
            SELECT 
                id, event_type, user_id, business_id, resource_type,
                resource_id, action, details, ip_address, user_agent, created_at
            FROM audit_logs
            WHERE 1=1
            AND (:user_id IS NULL OR user_id = :user_id)
            AND (:business_id IS NULL OR business_id = :business_id)
            AND (:start_date IS NULL OR created_at >= :start_date)
            AND (:end_date IS NULL OR created_at <= :end_date)
            ORDER BY created_at DESC
            LIMIT :limit
        """)
        
        results = db.execute(query, {
            "user_id": user_id,
            "business_id": business_id,
            "start_date": start_date,
            "end_date": end_date,
            "limit": limit
        }).fetchall()
        
        logs = []
        for row in results:
            log = {
                "id": str(row[0]),
                "event_type": row[1],
                "user_id": row[2],
                "business_id": row[3],
                "resource_type": row[4],
                "resource_id": row[5],
                "action": row[6],
                "details": json.loads(row[7]) if row[7] else None,
                "ip_address": row[8],
                "user_agent": row[9],
                "created_at": row[10].isoformat() if row[10] else None
            }
            logs.append(log)
        
        return logs


# Global instance
security_service = SecurityService()