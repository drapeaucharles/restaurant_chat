# Restaurant AI Chat Backend

FastAPI-based backend for AI-powered restaurant chat system with multi-model support, tool calling, and WhatsApp integration.

## 🚀 Features

- **AI Chat Services**: Multiple AI providers (MIA, OpenAI, Anthropic)
- **Tool Calling**: AI can query menu database for accurate information
- **Multi-Restaurant**: Support for multiple restaurants with isolated data
- **Customer Memory**: Remembers customer preferences and conversation history
- **WhatsApp Integration**: Full WhatsApp Business API support
- **Smart Caching**: Redis-based response caching with semantic similarity
- **Embeddings**: PGVector for semantic search through menus
- **Multi-language**: Automatic language detection and response

## Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   Frontend      │────▶│  FastAPI     │────▶│ PostgreSQL  │
│  (React/Next)   │     │   Backend    │     │  + PGVector │
└─────────────────┘     └──────────────┘     └─────────────┘
                               │
                    ┌──────────┴──────────┐
                    │                     │
              ┌─────▼─────┐        ┌─────▼─────┐
              │    MIA     │        │ WhatsApp  │
              │  Backend   │        │  Service  │
              └───────────┘        └───────────┘
```

## Quick Start

### Prerequisites

- Python 3.11+
- PostgreSQL with PGVector extension
- Redis (optional, for caching)
- Node.js 18+ (for WhatsApp service)

### Installation

```bash
# Clone repository
git clone https://github.com/drapeaucharles/restaurant_chat.git
cd Restaurant/BackEnd

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration
```

### Database Setup

```bash
# Create database
createdb restaurant_chat

# Enable PGVector extension
psql -d restaurant_chat -c "CREATE EXTENSION IF NOT EXISTS vector;"

# Run migrations
python run_migrations.py
```

### Running the Server

```bash
# Development
python main.py

# Production
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at `http://localhost:8000`
API docs: `http://localhost:8000/docs`

## API Endpoints

### Chat Endpoints

```python
POST /chat
{
    "restaurant_id": "bella_vista",
    "client_id": "user-123",
    "message": "What fish dishes do you have?",
    "service": "full_menu_with_tools"  # Optional, auto-selected if not provided
}
```

Available services:
- `full_menu_with_tools` - AI with tool calling (recommended)
- `full_menu` - Full menu in context
- `smart_menu` - Fetch details on demand
- `db_query` - Direct database queries

### Restaurant Management

```python
# Get restaurant
GET /restaurant/{restaurant_id}

# Update restaurant
PUT /restaurant/{restaurant_id}
{
    "data": {...},  # Menu and restaurant info
    "rag_mode": "full_menu_with_tools"
}

# Upload menu photos
POST /restaurant/{restaurant_id}/menu/upload
```

### WhatsApp Integration

```python
# Webhook for WhatsApp
POST /whatsapp/webhook

# Send message
POST /whatsapp/send
{
    "to": "1234567890",
    "message": "Hello from Restaurant AI"
}
```

## Tool Calling

The system supports OpenAI-compatible tool calling for accurate menu queries:

### Available Tools

1. **search_menu_items** - Search by ingredient, category, or name
2. **get_dish_details** - Get complete details about a specific dish
3. **filter_by_dietary** - Find dishes for dietary restrictions

### How It Works

1. User asks: "What vegetarian pasta dishes do you have?"
2. AI recognizes intent and calls `search_menu_items` tool
3. Backend executes database query
4. AI formats results naturally: "We have 3 vegetarian pasta options..."

### Configuring Tools

Tools are defined in `services/mia_chat_service_full_menu_with_tools_fixed.py`:

```python
AVAILABLE_TOOLS = [{
    "type": "function",
    "function": {
        "name": "search_menu_items",
        "description": "Search menu items",
        "parameters": {...}
    }
}]
```

## Customer Memory

The system remembers:
- Customer name and preferences
- Dietary restrictions and allergies
- Previous orders and favorites
- Conversation context

Memory is stored per customer per restaurant and persists across sessions.

## Deployment

### Railway

The backend is designed for Railway deployment:

```bash
# Deploy to Railway
railway up

# Required environment variables:
DATABASE_URL
REDIS_URL
MIA_BACKEND_URL
OPENAI_API_KEY  # Optional
```

### Docker

```bash
# Build image
docker build -t restaurant-backend .

# Run container
docker run -p 8000:8000 --env-file .env restaurant-backend
```

## Configuration

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost/restaurant_chat

# Redis (optional)
REDIS_URL=redis://localhost:6379

# AI Services
MIA_BACKEND_URL=https://mia-backend-production.up.railway.app
OPENAI_API_KEY=sk-...  # Optional
ANTHROPIC_API_KEY=sk-...  # Optional

# WhatsApp (optional)
WHATSAPP_TOKEN=...
WHATSAPP_WEBHOOK_SECRET=...

# Security
JWT_SECRET_KEY=your-secret-key
```

### Service Configuration

Each restaurant can configure their preferred AI service in the database:
- `rag_mode`: Which AI service to use
- `business_type`: Restaurant, bakery, cafe, etc.
- `data`: Menu items and restaurant information

## Project Structure

```
Restaurant/BackEnd/
├── main.py                 # FastAPI application
├── models.py              # SQLAlchemy models
├── database.py            # Database connection
├── config.py              # Configuration
├── requirements.txt       # Python dependencies
├── Dockerfile            # Docker configuration
│
├── routes/               # API endpoints
│   ├── auth.py          # Authentication
│   ├── chat_dynamic.py  # Dynamic chat routing
│   ├── restaurant.py    # Restaurant management
│   └── whatsapp.py      # WhatsApp integration
│
├── services/            # Business logic
│   ├── mia_chat_service_*.py     # MIA integrations
│   ├── customer_memory_service.py # Customer memory
│   ├── embedding_service.py       # Embeddings
│   └── restaurant_service.py      # Restaurant logic
│
├── schemas/             # Pydantic models
│   ├── chat.py         # Chat schemas
│   ├── restaurant.py   # Restaurant schemas
│   └── auth.py         # Auth schemas
│
├── migrations/          # Database migrations
├── uploads/            # File uploads
└── whatsapp-service/   # WhatsApp Node.js service
```

## Testing

```bash
# Run all tests
python -m pytest

# Test chat endpoint
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "restaurant_id": "test_restaurant",
    "client_id": "test_user",
    "message": "What pasta dishes do you have?"
  }'

# Test tool calling
python test_bella_vista_tools.py
```

## Troubleshooting

### Common Issues

1. **PGVector not found**
   ```sql
   CREATE EXTENSION IF NOT EXISTS vector;
   ```

2. **Tool calls not working**
   - Ensure MIA backend is accessible
   - Check restaurant has `rag_mode: "full_menu_with_tools"`
   - Verify tools are in correct OpenAI format

3. **WhatsApp not connecting**
   - Check Node.js service is running
   - Verify webhook URL is publicly accessible
   - Check token and webhook secret

## Contributing

1. Fork the repository
2. Create feature branch
3. Add tests for new features
4. Submit pull request

## License

Proprietary - All rights reserved