"""
Rate limiting utilities for brute-force protection.
"""

from collections import defaultdict, deque
from datetime import datetime, timedelta
from typing import Dict, Deque
from fastapi import HTTPException, Request, status

# In-memory storage for failed login attempts
# In production, use Redis or a database
failed_attempts: Dict[str, Deque[datetime]] = defaultdict(deque)

# Configuration
MAX_ATTEMPTS = 5  # Maximum failed attempts
LOCKOUT_DURATION = timedelta(minutes=15)  # Lockout duration
ATTEMPT_WINDOW = timedelta(minutes=5)  # Time window for counting attempts


def check_rate_limit(identifier: str) -> None:
    """
    Check if the identifier (IP or restaurant_id) has exceeded rate limits.
    Raises HTTPException if rate limited.
    """
    now = datetime.utcnow()
    attempts = failed_attempts[identifier]
    
    # Remove old attempts outside the window
    while attempts and attempts[0] < now - ATTEMPT_WINDOW:
        attempts.popleft()
    
    # Check if locked out (too many recent attempts)
    if len(attempts) >= MAX_ATTEMPTS:
        # Check if lockout period has passed
        if attempts[-1] + LOCKOUT_DURATION > now:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Too many failed login attempts. Try again in {LOCKOUT_DURATION.total_seconds()//60} minutes."
            )
        else:
            # Lockout period has passed, clear attempts
            attempts.clear()


def record_failed_attempt(identifier: str) -> None:
    """Record a failed login attempt for the identifier."""
    now = datetime.utcnow()
    failed_attempts[identifier].append(now)


def clear_failed_attempts(identifier: str) -> None:
    """Clear failed attempts for the identifier (on successful login)."""
    if identifier in failed_attempts:
        failed_attempts[identifier].clear()


def get_client_ip(request: Request) -> str:
    """Get client IP address from request."""
    # Check for forwarded headers first (for reverse proxies)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Fallback to direct client IP
    return request.client.host if request.client else "unknown"

