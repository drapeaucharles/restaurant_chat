"""
Authentication routes for restaurant login and registration.
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from auth import (
    authenticate_restaurant, 
    create_token, 
    get_current_owner,
    get_current_restaurant_from_refresh_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from database import get_db
import models
from schemas.restaurant import RestaurantCreateRequest, RestaurantLoginRequest, StaffCreateRequest
from schemas.token import TokenRefreshRequest
from schemas.auth import TokenResponse
from services.restaurant_service import create_restaurant_service
from rate_limiter import check_rate_limit, record_failed_attempt, clear_failed_attempts, get_client_ip

router = APIRouter(prefix="/restaurant", tags=["authentication"])


@router.post("/register")
def register_restaurant(req: RestaurantCreateRequest, db: Session = Depends(get_db)):
    """Register a new restaurant using the consolidated service."""
    return create_restaurant_service(req, db)


@router.post("/login")
def login_restaurant(request: RestaurantLoginRequest, req: Request, db: Session = Depends(get_db)):
    """Login restaurant and return JWT tokens with brute-force protection."""
    client_ip = get_client_ip(req)
    
    # Check rate limits for both IP and restaurant_id
    try:
        check_rate_limit(client_ip)
        check_rate_limit(request.restaurant_id)
    except HTTPException:
        # Record this as a failed attempt and re-raise
        record_failed_attempt(client_ip)
        record_failed_attempt(request.restaurant_id)
        raise
    
    restaurant = authenticate_restaurant(
        restaurant_id=request.restaurant_id,
        password=request.password,
        db=db
    )
    
    if not restaurant:
        # Record failed attempt for both IP and restaurant_id
        record_failed_attempt(client_ip)
        record_failed_attempt(request.restaurant_id)
        
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid restaurant ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Clear failed attempts on successful login
    clear_failed_attempts(client_ip)
    clear_failed_attempts(request.restaurant_id)
    
    # Create access token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(
        data={"sub": restaurant.restaurant_id, "role": restaurant.role, "type": "access"},
        token_type="access",
        expires_delta=access_token_expires
    )
    
    # Create refresh token
    refresh_token = create_token(
        data={"sub": restaurant.restaurant_id, "role": restaurant.role, "type": "refresh"},
        token_type="refresh"
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
        "refresh_token": refresh_token,
        "refresh_token_expires_in": REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # seconds
        "role": restaurant.role
    }


@router.post("/token")
def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """OAuth2 compatible token endpoint."""
    restaurant = authenticate_restaurant(
        restaurant_id=form_data.username,  # Using username field for restaurant_id
        password=form_data.password,
        db=db
    )
    
    if not restaurant:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid restaurant ID or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_token(
        data={"sub": restaurant.restaurant_id, "role": restaurant.role, "type": "access"},
        token_type="access",
        expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer"
    }



@router.post("/refresh-token", response_model=TokenResponse)
def refresh_token(request: TokenRefreshRequest, db: Session = Depends(get_db)):
    """Refresh access token using a valid refresh token."""
    try:
        # Validate refresh token and get restaurant
        restaurant = get_current_restaurant_from_refresh_token(request.refresh_token, db)
        
        # Create new access token
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_token(
            data={"sub": restaurant.restaurant_id, "role": restaurant.role, "type": "access"},
            token_type="access",
            expires_delta=access_token_expires
        )
        
        # Optionally create new refresh token (token rotation for better security)
        new_refresh_token = create_token(
            data={"sub": restaurant.restaurant_id, "role": restaurant.role, "type": "refresh"},
            token_type="refresh"
        )
        
        return TokenResponse(
            access_token=access_token,
            token_type="bearer",
            expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # seconds
            refresh_token=new_refresh_token,
            refresh_token_expires_in=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,  # seconds
            role=restaurant.role
        )
        
    except HTTPException:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/create-staff")
def create_staff(
    req: StaffCreateRequest, 
    current_owner: models.Restaurant = Depends(get_current_owner),
    db: Session = Depends(get_db)
):
    """Create a staff account. Only owners can create staff."""
    # Check if staff restaurant_id already exists
    existing_restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == req.restaurant_id
    ).first()
    
    if existing_restaurant:
        raise HTTPException(
            status_code=400, 
            detail="Restaurant ID already exists"
        )
    
    # Use the owner's restaurant data if staff data is not provided
    staff_data = req.data.dict() if req.data else current_owner.data
    
    # Create staff restaurant request
    staff_request = RestaurantCreateRequest(
        restaurant_id=req.restaurant_id,
        password=req.password,
        role="staff",
        data=staff_data
    )
    
    # Use the consolidated service to create staff
    result = create_restaurant_service(staff_request, db)
    result["message"] = "Staff account created successfully"
    
    return result

