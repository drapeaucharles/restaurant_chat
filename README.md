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

## Complete System Architecture

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐
│   React Frontend│────▶│  Restaurant  │────▶│ PostgreSQL  │
│   (TypeScript)  │     │  Backend     │     │ + PGVector  │
│   Tailwind CSS  │     │  (FastAPI)   │     │ Embeddings  │
└─────────────────┘     └──────┬───────┘     └─────────────┘
                               │
                    ┌──────────┼──────────┐
                    │          │          │
            ┌───────▼──┐   ┌───▼────┐  ┌──▼────────┐
            │   MIA    │   │WhatsApp│  │  Redis    │
            │ Backend  │   │Service │  │  Cache    │
            │(Job Queue│   │(Node.js│  │           │
            │& GPU     │   │  + QR  │  │           │
            │ Miners)  │   │Codes)  │  │           │
            └──────────┘   └────────┘  └───────────┘
                 │
        ┌────────┴─────────┐
        │                  │
    ┌───▼─────┐    ┌──────▼──────┐
    │GPU      │    │  GPU Miner  │
    │Miner 1  │... │     N       │
    │(vLLM)   │    │  (vLLM)     │
    │bore.pub │    │ bore.pub    │
    └─────────┘    └─────────────┘
```

### Technology Stack

#### Frontend (React/TypeScript)
- **Framework**: React 18 with TypeScript
- **Styling**: Tailwind CSS with dark theme
- **Animations**: Framer Motion
- **Build Tool**: Vite for fast development
- **State Management**: Context API + Zustand

#### Backend (FastAPI/Python)
- **Framework**: FastAPI with async support
- **Database**: PostgreSQL with PGVector for embeddings
- **Caching**: Redis for response caching
- **AI Integration**: MIA Backend for GPU mining
- **Authentication**: JWT-based auth system

#### AI Infrastructure
- **MIA Backend**: Centralized job orchestration
- **GPU Miners**: Distributed vLLM workers
- **Models**: Qwen2.5-7B-Instruct-AWQ (4-bit)
- **Tool Calling**: OpenAI-compatible function calling

#### External Services
- **WhatsApp**: Business API integration
- **Deployment**: Railway for both frontend and backend
- **Tunneling**: bore.pub for GPU miner access

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
Restaurant/                        # Main restaurant AI system
├── README.md                      # This file - system overview
├── CLAUDE_CONTEXT.md             # Technical context for AI assistants
│
├── BackEnd/                      # Python FastAPI backend
│   ├── main.py                   # FastAPI application entry point
│   ├── models.py                 # SQLAlchemy database models
│   ├── database.py               # Database connection setup
│   ├── config.py                 # Configuration management
│   ├── requirements.txt          # Python dependencies
│   ├── Dockerfile               # Backend container config
│   │
│   ├── routes/                  # API endpoint definitions
│   │   ├── auth.py             # Authentication endpoints
│   │   ├── chat_dynamic.py     # Dynamic chat routing
│   │   ├── restaurant.py       # Restaurant CRUD operations
│   │   ├── whatsapp.py         # WhatsApp integration
│   │   └── businesses.py       # Multi-business support
│   │
│   ├── services/               # Core business logic
│   │   ├── mia_chat_service_internal_tools_v5.py  # Main AI service
│   │   ├── customer_memory_service.py             # Customer memory
│   │   ├── embedding_service.py                   # Vector embeddings
│   │   ├── restaurant_service.py                  # Restaurant logic
│   │   └── whatsapp_service.py                    # WhatsApp messaging
│   │
│   ├── schemas/                # Pydantic data models
│   │   ├── chat.py            # Chat request/response schemas
│   │   ├── restaurant.py      # Restaurant data schemas
│   │   ├── auth.py           # Authentication schemas
│   │   └── whatsapp.py       # WhatsApp message schemas
│   │
│   ├── models/                # Database model definitions
│   │   └── customer_profile.py
│   │
│   ├── uploads/               # File upload storage
│   │   └── menu/             # Menu image uploads
│   │
│   └── gpu_embedding_service/ # Secure embedding API
│       ├── Dockerfile
│       ├── docker-compose.yml
│       └── secure_embedding_api.py
│
├── Front_end/project/           # React TypeScript frontend
│   ├── package.json            # Node.js dependencies
│   ├── vite.config.ts         # Vite build configuration
│   ├── tailwind.config.js     # Tailwind CSS config
│   │
│   ├── src/                   # React source code
│   │   ├── App.tsx           # Main application component
│   │   ├── main.tsx          # Application entry point
│   │   │
│   │   ├── components/       # Reusable UI components
│   │   │   ├── Chat/        # Chat interface components
│   │   │   ├── Forms/       # Business and menu forms
│   │   │   ├── Layout/      # Layout wrapper components
│   │   │   ├── WhatsApp/    # WhatsApp integration UI
│   │   │   └── ui/          # Base UI components
│   │   │
│   │   ├── pages/           # Route page components
│   │   │   ├── Admin/       # Admin dashboard pages
│   │   │   ├── Owner/       # Business owner pages
│   │   │   ├── Auth/        # Authentication pages
│   │   │   └── Public/      # Public-facing pages
│   │   │
│   │   ├── services/        # API communication layer
│   │   ├── contexts/        # React context providers
│   │   ├── types/          # TypeScript type definitions
│   │   └── utils/          # Helper functions
│   │
│   ├── public/             # Static assets
│   └── build/             # Production build output
│
├── whatsapp-service/         # Node.js WhatsApp service
│   ├── server.js            # WhatsApp webhook server
│   ├── package.json        # Node.js dependencies
│   └── qr-codes/          # QR code storage
│
├── install_miner_oneliner.sh  # GPU miner installation script
└── test_*.py                  # Testing and validation scripts
```

### Key Components Breakdown

#### Backend Services Architecture
- **Main AI Service**: `services/mia_chat_service_internal_tools_v5.py` - Complete two-phase AI system
- **Customer Memory**: Persistent conversation history and preferences
- **Tool Calling**: Database queries executed locally for safety
- **Multi-Business**: Support for restaurants, bakeries, cafes, legal services
- **WhatsApp Integration**: Full Business API with QR code generation

#### Frontend Architecture
- **Role-Based Access**: Admin, business owner, and public user interfaces
- **Real-Time Chat**: WebSocket-ready chat interface with tool call visualization
- **Menu Management**: Visual editor with drag-drop, photos, allergen tracking
- **Dark Theme**: Cosmic-themed UI with animated backgrounds
- **Responsive Design**: Mobile-first approach with Tailwind CSS

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