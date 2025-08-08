# Restaurant Management Platform - Comprehensive Project Analysis

## Overview

This is a full-stack restaurant management SaaS platform built with FastAPI (backend) and React + TypeScript (frontend). The platform enables restaurants to manage their online presence, handle customer interactions via AI-powered chat, integrate with WhatsApp for customer communication, and manage staff access.

## Technology Stack

### Backend
- **Framework**: FastAPI (Python)
- **Database**: PostgreSQL with SQLAlchemy ORM
- **Authentication**: JWT tokens with refresh token support
- **AI Integration**: OpenAI GPT-4 for chat responses
- **Vector Database**: Pinecone for semantic search
- **WhatsApp Integration**: Node.js service using open-wa
- **Rate Limiting**: Custom implementation with Redis-like in-memory storage
- **Other Dependencies**: 
  - Pydantic for data validation
  - Passlib/bcrypt for password hashing
  - python-jose for JWT handling
  - httpx for async HTTP requests

### Frontend
- **Framework**: React 18 with TypeScript
- **Build Tool**: Vite
- **Routing**: React Router v6
- **Styling**: Tailwind CSS
- **HTTP Client**: Axios
- **Icons**: Lucide React
- **State Management**: React Context API (AuthContext)

## Architecture

### Backend Structure

```
BackEnd/
├── main.py                 # FastAPI app initialization, routes, WhatsApp service management
├── database.py             # Database connection and session management
├── models.py               # SQLAlchemy ORM models
├── auth.py                 # JWT authentication and authorization
├── pinecone_utils.py       # Vector database operations
├── rate_limiter.py         # Brute-force protection
├── routes/                 # API endpoints
│   ├── auth.py            # Restaurant authentication endpoints
│   ├── restaurant.py      # Restaurant management endpoints
│   ├── chat.py            # Public chat endpoints
│   ├── chats.py           # Chat management endpoints
│   ├── clients.py         # Client management endpoints
│   ├── whatsapp.py        # WhatsApp integration endpoints
│   ├── speech.py          # Speech-to-text endpoints
│   └── smartlamp.py       # Smart lamp audio endpoints
├── schemas/                # Pydantic models
│   ├── auth.py            # Authentication schemas
│   ├── restaurant.py      # Restaurant data schemas
│   ├── chat.py            # Chat message schemas
│   ├── client.py          # Client schemas
│   └── whatsapp.py        # WhatsApp schemas
├── services/               # Business logic
│   ├── chat_service.py    # AI chat logic
│   ├── restaurant_service.py
│   ├── client_service.py
│   └── whatsapp_service.py
└── whatsapp-service/       # Node.js WhatsApp service
    ├── server.js          # WhatsApp API server
    └── package.json

```

### Frontend Structure

```
Front_end/project/src/
├── App.tsx                 # Main app component with routing
├── main.tsx               # Application entry point
├── contexts/
│   └── AuthContext.tsx    # Authentication state management
├── components/
│   ├── Auth/              # Authentication components
│   ├── Chat/              # Chat interface components
│   ├── Forms/             # Form components
│   ├── Layout/            # Layout components
│   └── WhatsApp/          # WhatsApp integration components
├── pages/
│   ├── Admin/             # Admin dashboard pages
│   ├── Auth/              # Login page
│   ├── Chat/              # Public chat page
│   └── Owner/             # Restaurant owner pages
├── services/
│   ├── api.ts             # API service layer
│   └── liveApi.js         # Real-time API service
├── types/                 # TypeScript type definitions
└── utils/                 # Utility functions
```

## Database Schema

### Models

1. **Restaurant**
   - `restaurant_id` (String, Primary Key)
   - `password` (String, hashed)
   - `role` (String: 'owner' | 'staff')
   - `data` (JSON: restaurant details)
   - `whatsapp_number` (String, optional)
   - `whatsapp_session_id` (String, optional)

2. **Client**
   - `id` (UUID, Primary Key)
   - `restaurant_id` (String, Foreign Key)
   - `first_seen` (DateTime)
   - `last_seen` (DateTime)
   - `preferences` (JSON)
   - `restaurants_visited` (JSON array)
   - `name` (String)
   - `email` (String)
   - `phone_number` (String, optional - for WhatsApp)

3. **ChatMessage**
   - `id` (UUID, Primary Key)
   - `restaurant_id` (String, Foreign Key)
   - `client_id` (UUID, Foreign Key)
   - `sender_type` (String: 'client' | 'restaurant' | 'ai')
   - `message` (Text)
   - `timestamp` (DateTime)

## Key Features

### 1. Restaurant Management
- **Registration/Login**: JWT-based authentication with refresh tokens
- **Profile Management**: Update restaurant info, menu, FAQ, opening hours
- **Staff Management**: Owners can create staff accounts with limited permissions
- **Multi-restaurant Support**: Each restaurant has unique ID and isolated data

### 2. AI-Powered Chat System
- **Public Chat Interface**: Customers can chat without authentication
- **AI Responses**: GPT-4 powered responses based on restaurant data
- **Context Awareness**: Uses Pinecone vector search for relevant responses
- **Chat History**: Maintains context from recent conversations (60 minutes)
- **Manual Override**: Restaurant staff can disable AI and respond manually

### 3. WhatsApp Integration
- **Two-way Communication**: Receive and send messages via WhatsApp
- **Session Management**: QR code-based authentication
- **Automatic Forwarding**: Messages from WhatsApp users appear in chat interface
- **Staff Responses**: Manual responses are sent back to WhatsApp

### 4. Chat Management Dashboard
- **Real-time Updates**: Auto-refresh every 3 seconds
- **Client Grouping**: Messages grouped by client
- **AI Toggle**: Enable/disable AI per client conversation
- **Full History**: View complete conversation history per client
- **Staff Messaging**: Send manual responses to customers

### 5. Security Features
- **Password Hashing**: Bcrypt-based secure password storage
- **JWT Authentication**: Access and refresh token system
- **Rate Limiting**: Brute-force protection on login endpoints
- **CORS Configuration**: Restricted to production domain
- **Role-based Access**: Owner vs Staff permissions

## API Endpoints

### Authentication
- `POST /restaurant/register` - Register new restaurant
- `POST /restaurant/login` - Login and get JWT tokens
- `POST /restaurant/refresh-token` - Refresh access token
- `POST /restaurant/create-staff` - Create staff account (owner only)

### Restaurant Management
- `GET /restaurant/info` - Get public restaurant info
- `GET /restaurant/list` - List all restaurants
- `GET /restaurant/profile` - Get authenticated restaurant profile
- `PUT /restaurant/profile` - Update restaurant profile
- `POST /restaurant/update` - Update restaurant data (legacy)
- `DELETE /restaurant/delete` - Delete restaurant (owner only)

### Chat System
- `POST /chat` - Send chat message (public)
- `POST /client/create-or-update` - Create/update client
- `GET /chat/logs` - Get chat logs (authenticated)
- `GET /chat/logs/latest` - Get latest messages per client
- `GET /chat/logs/client` - Get full conversation for client
- `POST /chat/logs/toggle-ai` - Toggle AI for client

### WhatsApp Integration
- `POST /whatsapp/incoming` - Webhook for incoming messages
- `POST /whatsapp/send` - Send WhatsApp message
- `POST /whatsapp/restaurant/{id}/connect` - Connect WhatsApp
- `GET /whatsapp/restaurant/{id}/status` - Get connection status
- `GET /whatsapp/restaurant/{id}/qr` - Get QR code

### Client Management
- `POST /clients/` - Create new client
- `GET /clients/` - List restaurant's clients

## AI Chat System Details

### System Prompt
The AI assistant is configured to act as a helpful restaurant staff member, providing information about:
- Menu items, ingredients, and allergens
- Opening hours and contact information
- Restaurant story and general inquiries
- Dietary restrictions and recommendations

### Context Management
- Fetches last 60 minutes of conversation history
- Maximum 20 messages for context
- Filters to include only client and AI messages
- Chronological ordering for natural conversation flow

### Menu Processing
- Supports flexible menu item structure
- Fallback values for missing fields
- Handles both legacy ('dish') and new ('title') field names
- Validates and formats menu data for AI consumption

## Frontend Features

### Public Chat Interface (`/chat`)
- No authentication required
- Real-time message updates
- Visual indicators for:
  - AI responses (blue/purple gradient)
  - Client messages (light blue)
  - Restaurant staff messages (green)
  - Audio transcripts (purple)
- Connection status monitoring
- AI enabled/disabled status display

### Restaurant Owner Dashboard (`/owner`)
- Overview statistics
- Quick action links
- WhatsApp integration tab
- Test chat interface link
- Role-based UI elements

### Chat Management (`/owner/chat`)
- Grouped view by client
- Real-time updates
- AI toggle per conversation
- Send manual messages
- View full conversation history

## Configuration & Environment

### Required Environment Variables

Backend (.env):
```
DATABASE_URL=postgresql://user:pass@host/db
SECRET_KEY=your-jwt-secret-key
OPENAI_API_KEY=your-openai-api-key
PINECONE_API_KEY=your-pinecone-api-key
PINECONE_INDEX=your-index-name
PUBLIC_API_URL=http://localhost:8000
WHATSAPP_API_KEY=your-whatsapp-api-key
```

### CORS Configuration
Production domain: `https://lucky-lokum-06b2de.netlify.app`

### Default Ports
- FastAPI Backend: 8000
- WhatsApp Service: 8002
- Frontend Dev Server: 5173

## Security Considerations

1. **Authentication**: JWT-based with refresh tokens
2. **Password Storage**: Bcrypt hashing
3. **Rate Limiting**: IP and restaurant ID based
4. **Input Validation**: Pydantic schemas
5. **SQL Injection Protection**: SQLAlchemy ORM
6. **XSS Protection**: React's built-in escaping
7. **CORS**: Restricted to specific origins

## Deployment Notes

### Backend Deployment
- Runs WhatsApp service as subprocess
- Automatic service restart on crash
- Graceful shutdown handling
- Health check endpoints available

### Frontend Deployment
- Built with Vite for optimized production builds
- Deployed on Netlify
- Environment-specific API URLs
- Responsive design for mobile/tablet

## Future Enhancements

1. **Reservation System**: Table booking integration
2. **Payment Processing**: Online ordering capabilities  
3. **Analytics Dashboard**: Customer interaction insights
4. **Multi-language Support**: Internationalization
5. **Push Notifications**: Real-time alerts
6. **Menu Image Upload**: Visual menu items
7. **Customer Loyalty**: Points and rewards system
8. **Social Media Integration**: Facebook, Instagram

## Development Guidelines

### Code Organization
- Clear separation between routes, services, and schemas
- Consistent error handling patterns
- Comprehensive logging for debugging
- Type safety with TypeScript/Pydantic

### Testing Approach
- Mock data available for development
- Environment-based API switching
- Comprehensive error boundaries
- Graceful fallbacks

### Performance Considerations
- Database query optimization
- Caching with vector database
- Lazy loading of components
- Debounced API calls

This platform provides a complete solution for restaurants to manage their digital presence and customer interactions, with AI-powered assistance and multi-channel communication support.