"""
Authentication module for JWT token handling and password management.
"""

import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from database import get_db
import models

# JWT Configuration
SECRET_KEY = os.getenv("SECRET_KEY", "your-very-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24  # 24 hours
REFRESH_TOKEN_EXPIRE_DAYS = 7  # 7 days for refresh token

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme for token extraction
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="restaurant/login")


def hash_password(password: str) -> str:
    """Hash a plain text password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain text password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


def create_token(data: dict, token_type: str = "access", expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT token (access or refresh)."""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    elif token_type == "refresh":
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    else:  # Default to access token expiration
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except JWTError:
        return None


def get_current_restaurant(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    """Get the current authenticated restaurant from JWT token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        if payload is None:
            raise credentials_exception
        restaurant_id: str = payload.get("sub")
        if restaurant_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if restaurant is None:
        raise credentials_exception
    
    return restaurant


def get_current_restaurant_from_refresh_token(token: str, db: Session = Depends(get_db)):
    """Get the current authenticated restaurant from a refresh token."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = decode_token(token)
        if payload is None or payload.get("type") != "refresh":
            raise credentials_exception
        restaurant_id: str = payload.get("sub")
        if restaurant_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if restaurant is None:
        raise credentials_exception
    
    return restaurant


def authenticate_restaurant(restaurant_id: str, password: str, db: Session) -> Optional[models.Restaurant]:
    """Authenticate a restaurant with ID and password."""
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        return None
    
    if not verify_password(password, restaurant.password):
        return None
    
    return restaurant



def get_current_owner(current_restaurant: models.Restaurant = Depends(get_current_restaurant)):
    """Get the current authenticated restaurant and ensure it's an owner or admin."""
    if current_restaurant.role not in ["owner", "admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only owners can perform this action"
        )
    return current_restaurant

