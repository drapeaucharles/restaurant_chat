# FastAPI Restaurant Management API - Advanced Authentication

## Overview

This FastAPI application provides a comprehensive restaurant management system with advanced authentication features including JWT tokens, role-based access control, and brute-force protection.

## Authentication Flow

### 1. Registration

**Endpoint**: `POST /restaurant/register`

Register a new restaurant account with the following data:

```json
{
  "restaurant_id": "unique_restaurant_id",
  "password": "secure_password",
  "role": "owner",  // optional, defaults to "owner"
  "data": {
    "name": "Restaurant Name",
    "story": "Restaurant story",
    "menu": [],
    "faq": []
  }
}
```

**Features**:
- Passwords are automatically hashed using bcrypt
- Duplicate restaurant IDs are prevented
- Role defaults to "owner" if not specified
- Restaurant data is stored in Pinecone for owners (not staff)

### 2. Login

**Endpoint**: `POST /restaurant/login`

Authenticate with restaurant credentials:

```json
{
  "restaurant_id": "your_restaurant_id",
  "password": "your_password"
}
```

**Response**:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 86400,
  "role": "owner"
}
```

**Features**:
- JWT tokens with 24-hour expiration
- Brute-force protection (5 failed attempts per IP/restaurant_id)
- 15-minute lockout after exceeding attempts
- Role information included in token

### 3. Token Format

JWT tokens contain the following claims:
- `sub`: Restaurant ID (subject)
- `role`: User role ("owner" or "staff")
- `exp`: Expiration timestamp

### 4. Role-Based Access

#### Owner Role
- Can create staff accounts
- Full access to all restaurant management features
- Data is synced to Pinecone

#### Staff Role
- Limited access to restaurant features
- Cannot create other staff accounts
- Data is not synced to Pinecone

## Protected Endpoints

The following endpoints require valid JWT authentication:

### Restaurant Management
- `GET /restaurant/profile` - Get current restaurant profile
- `PUT /restaurant/profile` - Update restaurant profile
- `DELETE /restaurant/delete` - Delete restaurant account

### Client Management
- `GET /clients/` - List restaurant's clients

### Chat Management
- `POST /chat/logs` - Access chat logs

### Staff Management (Owner Only)
- `POST /restaurant/create-staff` - Create staff accounts (requires owner role)

## Security Features

### Password Security
- All passwords are hashed using bcrypt
- Passwords are never stored in plain text
- Password verification uses secure comparison

### Brute-Force Protection
- Maximum 5 failed login attempts per IP address
- Maximum 5 failed login attempts per restaurant ID
- 15-minute lockout period after exceeding limits
- Automatic cleanup of old failed attempts

### JWT Security
- Tokens expire after 24 hours
- Secure secret key for token signing
- Role-based authorization checks

## Usage Examples

### Register a Restaurant
```bash
curl -X POST "http://localhost:8000/restaurant/register" \
     -H "Content-Type: application/json" \
     -d '{
       "restaurant_id": "my_restaurant",
       "password": "secure_password_123",
       "role": "owner",
       "data": {
         "name": "My Restaurant",
         "story": "A great place to eat",
         "menu": [],
         "faq": []
       }
     }'
```

### Login
```bash
curl -X POST "http://localhost:8000/restaurant/login" \
     -H "Content-Type: application/json" \
     -d '{
       "restaurant_id": "my_restaurant",
       "password": "secure_password_123"
     }'
```

### Access Protected Route
```bash
curl -X GET "http://localhost:8000/restaurant/profile" \
     -H "Authorization: Bearer YOUR_JWT_TOKEN"
```

### Create Staff Account (Owner Only)
```bash
curl -X POST "http://localhost:8000/restaurant/create-staff" \
     -H "Authorization: Bearer OWNER_JWT_TOKEN" \
     -H "Content-Type: application/json" \
     -d '{
       "restaurant_id": "staff_member_1",
       "password": "staff_password_123"
     }'
```

## Error Handling

### Authentication Errors
- `401 Unauthorized`: Invalid credentials or expired token
- `403 Forbidden`: Insufficient permissions (e.g., staff trying to create staff)
- `429 Too Many Requests`: Rate limit exceeded

### Validation Errors
- `400 Bad Request`: Invalid input data or duplicate restaurant ID
- `422 Unprocessable Entity`: Schema validation errors

## Testing

The application includes comprehensive test suites:

### Authentication Tests (`test_auth_comprehensive.py`)
- Password hashing and verification
- Successful and failed registration
- Successful and failed login
- Token validation
- Role-based access control
- Brute-force protection

### Run Tests
```bash
python test_auth_comprehensive.py
```

## Configuration

### Environment Variables
- `SECRET_KEY`: JWT signing secret (change in production)
- `DATABASE_URL`: Database connection string
- `PINECONE_API_KEY`: Pinecone API key for vector storage

### Rate Limiting Configuration
- `MAX_ATTEMPTS`: Maximum failed attempts (default: 5)
- `LOCKOUT_DURATION`: Lockout duration (default: 15 minutes)
- `ATTEMPT_WINDOW`: Time window for counting attempts (default: 5 minutes)

## Dependencies

### Core Dependencies
- `fastapi`: Web framework
- `uvicorn`: ASGI server
- `sqlalchemy`: Database ORM
- `pydantic`: Data validation

### Authentication Dependencies
- `python-jose[cryptography]`: JWT handling
- `passlib[bcrypt]`: Password hashing
- `python-multipart`: Form data support

### Rate Limiting Dependencies
- `slowapi`: Rate limiting for FastAPI

## Deployment Notes

1. **Change Secret Key**: Use a secure, random secret key in production
2. **Database**: Configure proper database connection
3. **HTTPS**: Always use HTTPS in production
4. **Rate Limiting**: Consider using Redis for distributed rate limiting
5. **Monitoring**: Implement logging and monitoring for security events

## API Documentation

Interactive API documentation is available at:
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

