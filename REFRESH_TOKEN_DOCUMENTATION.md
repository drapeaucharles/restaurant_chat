# Refresh Token Implementation Documentation

## Overview

The FastAPI Restaurant Management System now supports refresh tokens to enable longer user sessions while maintaining security. This implementation follows industry best practices for token-based authentication.

## Features

### Token Types
- **Access Token**: Short-lived (24 hours) for API access
- **Refresh Token**: Long-lived (7 days) for obtaining new access tokens

### Security Features
- Token rotation: New refresh token issued on each refresh
- Type validation: Access tokens cannot be used as refresh tokens
- Automatic expiration handling
- Role preservation across token refreshes

## API Endpoints

### 1. Login Endpoint
**POST** `/restaurant/login`

**Request Body:**
```json
{
    "restaurant_id": "string",
    "password": "string"
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token_expires_in": 604800,
    "role": "owner"
}
```

### 2. Refresh Token Endpoint
**POST** `/restaurant/refresh-token`

**Request Body:**
```json
{
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response:**
```json
{
    "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "token_type": "bearer",
    "expires_in": 86400,
    "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "refresh_token_expires_in": 604800,
    "role": "owner"
}
```

## Token Configuration

### Expiration Times
- **Access Token**: 24 hours (86,400 seconds)
- **Refresh Token**: 7 days (604,800 seconds)

### Token Structure
Both tokens are JWT tokens containing:
- `sub`: Restaurant ID
- `role`: User role (owner/staff)
- `type`: Token type (access/refresh)
- `exp`: Expiration timestamp

## Implementation Details

### Authentication Flow
1. User logs in with credentials
2. Server validates credentials
3. Server issues both access and refresh tokens
4. Client stores both tokens securely
5. Client uses access token for API requests
6. When access token expires, client uses refresh token to get new tokens
7. Server validates refresh token and issues new token pair

### Token Rotation
For enhanced security, the system implements token rotation:
- Each refresh operation issues a new refresh token
- Old refresh tokens become invalid after use
- This prevents token replay attacks

### Error Handling
- Invalid refresh tokens return 401 Unauthorized
- Expired refresh tokens return 401 Unauthorized
- Access tokens used as refresh tokens are rejected

## Client Implementation Guide

### Storing Tokens
```javascript
// Store tokens securely
localStorage.setItem('access_token', response.access_token);
localStorage.setItem('refresh_token', response.refresh_token);
```

### Using Access Tokens
```javascript
// Add to API requests
const headers = {
    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
};
```

### Handling Token Refresh
```javascript
async function refreshTokens() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    try {
        const response = await fetch('/restaurant/refresh-token', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ refresh_token: refreshToken })
        });
        
        if (response.ok) {
            const tokens = await response.json();
            localStorage.setItem('access_token', tokens.access_token);
            localStorage.setItem('refresh_token', tokens.refresh_token);
            return tokens.access_token;
        } else {
            // Refresh failed, redirect to login
            window.location.href = '/login';
        }
    } catch (error) {
        console.error('Token refresh failed:', error);
        window.location.href = '/login';
    }
}
```

### Automatic Token Refresh
```javascript
// Intercept API responses to handle token expiration
axios.interceptors.response.use(
    response => response,
    async error => {
        if (error.response?.status === 401) {
            const newToken = await refreshTokens();
            if (newToken) {
                // Retry original request with new token
                error.config.headers.Authorization = `Bearer ${newToken}`;
                return axios.request(error.config);
            }
        }
        return Promise.reject(error);
    }
);
```

## Security Considerations

### Best Practices
1. **Secure Storage**: Store refresh tokens in HTTP-only cookies when possible
2. **HTTPS Only**: Always use HTTPS in production
3. **Token Rotation**: Implemented to prevent token replay attacks
4. **Short Access Token Lifetime**: Minimizes exposure window
5. **Proper Validation**: Tokens are validated for type and expiration

### Production Recommendations
1. Use Redis or database to track active refresh tokens
2. Implement token blacklisting for logout
3. Add device/session tracking
4. Monitor for suspicious token usage patterns
5. Implement rate limiting on refresh endpoint

## Testing

The system includes comprehensive tests covering:
- Token generation and validation
- Refresh token functionality
- Error handling for invalid tokens
- Role preservation across refreshes
- Token expiration handling

Run tests with:
```bash
python3.11 test_refresh_token.py
```

## Migration Guide

### For Existing Clients
1. Update login handling to store both tokens
2. Implement automatic token refresh logic
3. Handle new response format from login endpoint
4. Test token refresh flow thoroughly

### Backward Compatibility
The system maintains backward compatibility:
- Existing access tokens continue to work
- OAuth2 token endpoint remains unchanged
- No breaking changes to protected routes

