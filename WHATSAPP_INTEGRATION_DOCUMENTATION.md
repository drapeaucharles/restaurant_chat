# WhatsApp Integration Documentation

## Overview

This document describes the WhatsApp integration added to the restaurant chatbot FastAPI backend. The integration allows restaurants to receive and respond to WhatsApp messages through their existing AI chatbot system.

## Architecture

### Components

1. **WhatsApp Service Layer** (`services/whatsapp_service.py`)
   - Handles communication with open-wa (wa-automate-nodejs)
   - Manages session creation and message sending
   - Provides phone number to client ID mapping

2. **WhatsApp Routes** (`routes/whatsapp.py`)
   - FastAPI endpoints for WhatsApp functionality
   - Webhook handler for incoming messages
   - Session management endpoints

3. **WhatsApp Schemas** (`schemas/whatsapp.py`)
   - Pydantic models for request/response validation
   - Type safety for WhatsApp-related data

4. **Database Models** (`models.py`)
   - Extended Restaurant model with WhatsApp fields
   - Backward compatible with existing data

## Database Changes

### Restaurant Model Updates

Added two new optional fields to the `Restaurant` model:

```python
# WhatsApp integration fields
whatsapp_number = Column(String, nullable=True)  # WhatsApp phone number for this restaurant
whatsapp_session_id = Column(String, nullable=True)  # Session ID for open-wa
```

### Migration

Run the migration script to add these fields to existing databases:

```bash
python3 migrate_whatsapp.py
```

For PostgreSQL production databases, run:
```sql
ALTER TABLE restaurants ADD COLUMN whatsapp_number VARCHAR;
ALTER TABLE restaurants ADD COLUMN whatsapp_session_id VARCHAR;
```

## API Endpoints

### 1. Incoming WhatsApp Messages

**POST** `/whatsapp/incoming`

Receives messages from open-wa webhook and processes them through the existing chat service.

**Request Body:**
```json
{
  "from_number": "+1234567890",
  "message": "Hello, I'd like to make a reservation",
  "session_id": "restaurant_123",
  "message_id": "msg_abc123",
  "timestamp": "2024-01-01T12:00:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Message processed successfully"
}
```

### 2. Send WhatsApp Messages

**POST** `/whatsapp/send`

Sends a message via WhatsApp using open-wa.

**Request Body:**
```json
{
  "to_number": "+1234567890",
  "message": "Thank you for your message! How can we help you today?",
  "session_id": "restaurant_123"
}
```

**Response:**
```json
{
  "success": true,
  "message_id": "msg_xyz789",
  "error": null
}
```

### 3. Connect Restaurant to WhatsApp

**POST** `/whatsapp/restaurant/{restaurant_id}/connect`

Creates a WhatsApp session for a restaurant and returns QR code for connection.

**Headers:**
```
Authorization: Bearer <restaurant_jwt_token>
```

**Response:**
```json
{
  "session_id": "restaurant_123",
  "qr_code": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
  "status": "created",
  "message": "Session created successfully. Scan QR code to connect WhatsApp."
}
```

### 4. Check WhatsApp Status

**GET** `/whatsapp/restaurant/{restaurant_id}/status`

Gets the current WhatsApp connection status for a restaurant.

**Headers:**
```
Authorization: Bearer <restaurant_jwt_token>
```

**Response:**
```json
{
  "connected": true,
  "session_id": "restaurant_123",
  "phone_number": "+1234567890",
  "status": "connected",
  "details": {
    "status": "connected",
    "battery": 85,
    "plugged": true
  }
}
```

## Integration Flow

### 1. Restaurant Connection Process

1. Restaurant calls `POST /whatsapp/restaurant/{id}/connect`
2. System creates session with open-wa
3. QR code is returned for scanning
4. Restaurant scans QR code with WhatsApp
5. Session becomes active

### 2. Incoming Message Flow

1. WhatsApp user sends message to restaurant's number
2. open-wa receives message and calls webhook (`POST /whatsapp/incoming`)
3. System finds restaurant by session ID
4. Generates consistent client ID from phone number
5. Creates ChatRequest and processes through existing chat_service
6. If AI responds, sends reply back to WhatsApp via background task

### 3. Client ID Generation

WhatsApp phone numbers are mapped to consistent client IDs using UUID5:

```python
def generate_client_id_from_phone(self, phone_number: str) -> str:
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')
    client_uuid = uuid.uuid5(namespace, phone_number)
    return str(client_uuid)
```

This ensures the same phone number always gets the same client ID across sessions.

## Configuration

### Environment Variables

```bash
# Open-WA server URL (default: http://localhost:8002)
OPEN_WA_URL=http://localhost:8002

# Backend URL for webhook registration
BACKEND_URL=http://localhost:8000
```

### Open-WA Setup

The integration expects an open-wa server running with the following endpoints:

- `POST /session/create` - Create new WhatsApp session
- `POST /message/send` - Send message via WhatsApp
- `GET /session/{id}/status` - Get session status

## Error Handling

### Graceful Degradation

- If open-wa service is unavailable, WhatsApp features fail gracefully
- Existing chat functionality continues to work normally
- Error messages are logged and returned in API responses

### Common Error Scenarios

1. **Restaurant not found for session**
   - Occurs when webhook receives message for unknown session
   - Returns error response to open-wa

2. **WhatsApp service unavailable**
   - Network errors connecting to open-wa
   - Returns error in send response

3. **Invalid phone number format**
   - Handled by client ID generation
   - Uses phone number as-is for UUID generation

## Testing

### Unit Tests

Run the test suite:

```bash
python3 -m pytest test_whatsapp_simple.py -v
```

### Manual Testing

Test endpoints with curl:

```bash
# Test incoming message
curl -X POST http://localhost:8000/whatsapp/incoming \
  -H "Content-Type: application/json" \
  -d '{
    "from_number": "+1234567890",
    "message": "Hello",
    "session_id": "test_session"
  }'

# Test send message
curl -X POST http://localhost:8000/whatsapp/send \
  -H "Content-Type: application/json" \
  -d '{
    "to_number": "+1234567890",
    "message": "Hello back",
    "session_id": "test_session"
  }'
```

## Backward Compatibility

### Existing Functionality

- All existing API endpoints continue to work unchanged
- Restaurant model is backward compatible (new fields are nullable)
- Chat service processes WhatsApp messages using existing logic
- No changes required to frontend code

### Migration Path

1. Deploy backend with WhatsApp integration
2. Run database migration script
3. Configure open-wa service
4. Connect restaurants via API
5. Frontend integration (future phase)

## Security Considerations

### Authentication

- Restaurant connection endpoints require JWT authentication
- Webhook endpoint is public but validates session IDs
- Phone numbers are hashed for client ID generation

### Data Privacy

- Phone numbers are stored as client IDs (hashed)
- Message content follows existing chat storage patterns
- WhatsApp session data is managed by open-wa

## Future Enhancements

### Planned Features

1. **Multiple Sessions per Restaurant**
   - Support for multiple WhatsApp numbers
   - Session management UI

2. **Message Templates**
   - Pre-defined response templates
   - Quick reply buttons

3. **Media Support**
   - Image and document handling
   - Voice message transcription

4. **Analytics**
   - WhatsApp message metrics
   - Response time tracking

### Scaling Considerations

- Current implementation supports one session at a time
- Code is structured for easy scaling to multiple sessions
- Consider Docker containers for session isolation
- Implement load balancing for high-volume restaurants

## Troubleshooting

### Common Issues

1. **Database column errors**
   - Run migration script: `python3 migrate_whatsapp.py`

2. **Open-WA connection failed**
   - Check OPEN_WA_URL environment variable
   - Verify open-wa service is running

3. **Session not found**
   - Verify restaurant has connected WhatsApp session
   - Check session_id in database

### Logging

WhatsApp operations are logged with detailed information:

```
🔍 ===== WHATSAPP INCOMING MESSAGE =====
📱 From: +1234567890
💬 Message: 'Hello from WhatsApp'
🔗 Session ID: restaurant_123
✅ Restaurant found: restaurant_123
👤 Generated client ID: abc-123-def
🤖 Processing through chat service...
📤 Sending AI response back to WhatsApp...
===== END WHATSAPP INCOMING =====
```

## Support

For issues or questions about the WhatsApp integration:

1. Check logs for detailed error messages
2. Verify open-wa service configuration
3. Test with simplified payloads
4. Review database migration status

