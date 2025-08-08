# Restaurant Platform - Detailed File Reference Guide

## Backend Files Reference

### Root Level Files

#### `/BackEnd/main.py`
- **Purpose**: FastAPI application entry point and core configuration
- **Key Functions**:
  - `start_whatsapp_service()`: Launches Node.js WhatsApp service subprocess
  - `stop_whatsapp_service()`: Gracefully shuts down WhatsApp service
  - `monitor_whatsapp_service()`: Auto-restarts crashed WhatsApp service
  - `lifespan()`: FastAPI lifecycle management
- **Routes Included**: 
  - `/` - Root endpoint
  - `/healthcheck`, `/health` - Health check endpoints
  - `/whatsapp/service/status` - WhatsApp service status
- **Configuration**:
  - CORS middleware setup (line 193-199)
  - Router includes (line 201-209)
  - Database table creation (line 182)

#### `/BackEnd/database.py`
- **Purpose**: Database connection and session management
- **Key Components**:
  - `DATABASE_URL`: Loaded from environment
  - `engine`: SQLAlchemy engine instance
  - `SessionLocal`: Session factory
  - `Base`: Declarative base for models
  - `get_db()`: Dependency for database sessions

#### `/BackEnd/models.py`
- **Purpose**: SQLAlchemy ORM models
- **Models**:
  - `Client` (line 11-23): Customer/client data
    - Links to restaurant via `restaurant_id`
    - Stores WhatsApp phone number
    - JSON preferences field for AI toggle state
  - `Restaurant` (line 25-35): Restaurant accounts
    - Primary key: `restaurant_id`
    - Includes WhatsApp integration fields
  - `ChatMessage` (line 40-50): All chat messages
    - Tracks `sender_type`: client/restaurant/ai
    - Links to both restaurant and client

#### `/BackEnd/auth.py`
- **Purpose**: JWT authentication and password management
- **Key Functions**:
  - `hash_password()`: Bcrypt password hashing
  - `verify_password()`: Password verification
  - `create_token()`: Generate JWT tokens (access/refresh)
  - `decode_token()`: Validate and decode JWT
  - `get_current_restaurant()`: Get authenticated restaurant from token
  - `get_current_owner()`: Ensure user has owner role
  - `authenticate_restaurant()`: Login logic
- **Configuration**:
  - `SECRET_KEY`: JWT signing key
  - `ACCESS_TOKEN_EXPIRE_MINUTES`: 24 hours
  - `REFRESH_TOKEN_EXPIRE_DAYS`: 7 days

#### `/BackEnd/pinecone_utils.py`
- **Purpose**: Vector database operations for AI context
- **Key Functions**:
  - `create_embedding()`: Generate OpenAI embeddings
  - `insert_restaurant_data()`: Store restaurant info in Pinecone
  - `insert_client_preferences()`: Store client preferences
  - `query_pinecone()`: Semantic search for chat context
- **Configuration**:
  - Uses OpenAI text-embedding-ada-002 model
  - Connects to Pinecone index from env

#### `/BackEnd/rate_limiter.py`
- **Purpose**: Brute-force protection for login endpoints
- **Features**:
  - In-memory storage of failed attempts
  - IP-based and restaurant_id-based limiting
  - Configurable thresholds and timeouts

### Routes Directory

#### `/BackEnd/routes/auth.py`
- **Purpose**: Authentication endpoints
- **Endpoints**:
  - `POST /restaurant/register` (line 30): New restaurant registration
  - `POST /restaurant/login` (line 36): Login with rate limiting
  - `POST /restaurant/token` (line 98): OAuth2 compatible endpoint
  - `POST /restaurant/refresh-token` (line 131): Refresh access token
  - `POST /restaurant/create-staff` (line 169): Create staff accounts

#### `/BackEnd/routes/restaurant.py`
- **Purpose**: Restaurant management endpoints
- **Endpoints**:
  - `GET /restaurant/info` (line 38): Public restaurant data
  - `GET /restaurant/list` (line 59): List all restaurants
  - `POST /restaurant/update` (line 77): Update restaurant (legacy)
  - `GET /restaurant/profile` (line 110): Get own profile
  - `PUT /restaurant/profile` (line 126): Update own profile
  - `DELETE /restaurant/delete` (line 165): Delete restaurant
- **Helper Functions**:
  - `process_menu_for_response()`: Format menu for API responses

#### `/BackEnd/routes/chat.py`
- **Purpose**: Public chat endpoints
- **Endpoints**:
  - `POST /client/create-or-update` (line 19): Create/update client
  - `POST /chat` (line 26): Main chat endpoint
    - Handles AI response logic
    - WhatsApp forwarding for restaurant messages
    - Saves messages to database
- **Key Logic**:
  - Line 36-41: Default sender_type enforcement
  - Line 53-62: Save client message before AI processing
  - Line 68-117: WhatsApp forwarding for restaurant messages

#### `/BackEnd/routes/chats.py`
- **Purpose**: Chat management endpoints (authenticated)
- **Endpoints**:
  - `POST /chat/` (line 21): Store new message
  - `GET /chat/` (line 182): Get messages between client and restaurant
  - `GET /chat/logs/latest` (line 225): Latest messages grouped by client
  - `GET /chat/logs/client` (line 285): Full conversation history
  - `POST /chat/logs/toggle-ai` (line 350): Toggle AI per client
- **Key Features**:
  - WhatsApp forwarding for staff messages (line 99-166)
  - AI state management in client preferences (line 373-387)

#### `/BackEnd/routes/clients.py`
- **Purpose**: Client management
- **Endpoints**:
  - `POST /clients/` (line 18): Create new client
  - `GET /clients/` (line 57): List restaurant's clients
  - `GET /clients/chat/logs/client` (line 81): Client logs (legacy)

#### `/BackEnd/routes/whatsapp.py`
- **Purpose**: WhatsApp integration endpoints
- **Endpoints**:
  - `POST /whatsapp/incoming` (line 29): Webhook for incoming messages
  - `POST /whatsapp/send` (line 122): Send message via WhatsApp
  - `POST /whatsapp/session/{id}/start` (line 165): Start session
  - `POST /whatsapp/restaurant/{id}/connect` (line 239): Connect restaurant
  - `GET /whatsapp/restaurant/{id}/qr` (line 327): Get QR code
  - `GET /whatsapp/restaurant/{id}/status` (line 383): Connection status
- **Helper Functions**:
  - `send_whatsapp_reply()` (line 304): Background task for replies

#### `/BackEnd/routes/speech.py`
- **Purpose**: Speech-to-text endpoints
- **Features**: Audio transcription for voice messages

#### `/BackEnd/routes/smartlamp.py`
- **Purpose**: Smart lamp audio integration
- **Features**: Special audio handling for smart devices

### Schemas Directory

#### `/BackEnd/schemas/chat.py`
- **Classes**:
  - `ChatRequest`: Incoming chat message
  - `ChatResponse`: AI response
  - `ChatMessageCreate`: Create new message
  - `ChatMessageResponse`: Message with metadata
  - `ToggleAIRequest`: Toggle AI state

#### `/BackEnd/schemas/restaurant.py`
- **Classes**:
  - `MenuItem`: Menu item with validation (line 4-98)
    - Handles legacy field mapping
    - Validates categories and subcategories
  - `FAQItem`: Question/answer pairs
  - `OpeningHours`: Structured hours by day
  - `RestaurantData`: Complete restaurant data
  - `RestaurantCreateRequest`: Registration payload
  - `RestaurantLoginRequest`: Login credentials
  - `RestaurantProfileUpdate`: Profile update payload

#### `/BackEnd/schemas/client.py`
- **Classes**:
  - `ClientCreateRequest`: New client data
  - `ClientResponse`: Client with metadata

#### `/BackEnd/schemas/whatsapp.py`
- **Classes**:
  - `WhatsAppIncomingMessage`: Webhook payload
  - `WhatsAppOutgoingMessage`: Send message payload
  - `WhatsAppSessionResponse`: Session status
  - Various response models

### Services Directory

#### `/BackEnd/services/chat_service.py`
- **Purpose**: Core AI chat logic
- **Key Functions**:
  - `chat_service()` (line 193): Main chat processing
    - AI blocking logic (line 213-250)
    - AI enabled state check (line 252-267)
    - Context preparation (line 300-314)
    - Chat history integration (line 316-334)
  - `fetch_recent_chat_history()` (line 27): Get last 60 min of messages
  - `format_chat_history_for_openai()` (line 66): Format for GPT
  - `get_or_create_client()` (line 105): Client management
  - `format_menu()` (line 142): Menu formatting for AI
  - `format_faq()` (line 171): FAQ formatting for AI
- **AI Configuration**:
  - System prompt (line 13-25)
  - Uses GPT-4 model
  - 200 token limit

#### `/BackEnd/services/restaurant_service.py`
- **Functions**:
  - `create_restaurant_service()`: Registration logic
  - `apply_menu_fallbacks()`: Menu data normalization

#### `/BackEnd/services/client_service.py`
- **Functions**:
  - `create_or_update_client_service()`: Client management

#### `/BackEnd/services/whatsapp_service.py`
- **Purpose**: WhatsApp API integration
- **Key Functions**:
  - `send_message()`: Send WhatsApp message
  - `create_session()`: Initialize WhatsApp session
  - `get_session_status()`: Check connection
  - `find_restaurant_by_session()`: Session lookup
  - `generate_client_id_from_phone()`: Phone to UUID

### WhatsApp Service Directory

#### `/BackEnd/whatsapp-service/server.js`
- **Purpose**: Node.js WhatsApp API server
- **Features**:
  - open-wa integration
  - Session management
  - QR code generation
  - Message forwarding to FastAPI

## Frontend Files Reference

### Root Level Files

#### `/Front_end/project/src/App.tsx`
- **Purpose**: Main application component with routing
- **Routes Configuration**:
  - Public routes (line 34-37): `/chat`, `/menu`, `/order`
  - Auth route (line 40): `/login`
  - Admin routes (line 45-79): Dashboard, create, edit, list
  - Owner routes (line 82-116): Dashboard, edit, logs, chat, staff
- **Components Used**:
  - `AuthProvider`: Authentication context wrapper
  - `ProtectedRoute`: Route guard component
  - Layout components: `AdminLayout`, `RestaurantOwnerLayout`

#### `/Front_end/project/src/main.tsx`
- **Purpose**: React application entry point
- **Setup**: Renders App in StrictMode

### Contexts Directory

#### `/Front_end/project/src/contexts/AuthContext.tsx`
- **Purpose**: Global authentication state management
- **State**:
  - `user`: Current user object with tokens
  - `isAuthenticated`: Auth status
  - `isAuthLoading`: Loading state
- **Functions**:
  - `login()`: Store user data and set axios headers
  - `logout()`: Clear auth and redirect
  - `updateUser()`: Update user data
- **Storage**: localStorage for persistence

### Components Directory

#### `/Front_end/project/src/components/Auth/LoginForm.tsx`
- **Purpose**: Restaurant login form
- **Features**: Restaurant ID and password fields

#### `/Front_end/project/src/components/Chat/ChatInterface.tsx`
- **Purpose**: Main chat UI component
- **State Management**:
  - `messages`: Chat history
  - `connectionStatus`: Backend connection
  - `aiEnabled`: AI toggle state
- **Key Functions**:
  - `loadConversation()` (line 122): Fetch chat history
  - `checkAIStatus()` (line 103): Check AI enabled state
  - `handleSendMessage()` (line 180): Send new message
- **Visual Features**:
  - Message type indicators (line 329-357)
  - Audio transcript styling (line 335-346)
  - Real-time updates via polling (line 84-90)

#### `/Front_end/project/src/components/Chat/ClientConversationPanel.tsx`
- **Purpose**: Full conversation view for a specific client
- **Features**: Message history, send functionality

#### `/Front_end/project/src/components/Forms/RestaurantForm.tsx`
- **Purpose**: Restaurant profile edit form
- **Fields**: Name, story, menu, FAQ, hours, contact

#### `/Front_end/project/src/components/Layout/AdminLayout.tsx`
- **Purpose**: Admin dashboard wrapper
- **Navigation**: Admin-specific menu items

#### `/Front_end/project/src/components/Layout/RestaurantOwnerLayout.tsx`
- **Purpose**: Restaurant owner dashboard wrapper
- **Navigation**: Owner/staff menu items

#### `/Front_end/project/src/components/Layout/ChatLayout.tsx`
- **Purpose**: Chat page layout wrapper

#### `/Front_end/project/src/components/ProtectedRoute.tsx`
- **Purpose**: Route authentication guard
- **Props**: `requiredRole` for role-based access

#### `/Front_end/project/src/components/WhatsApp/WhatsAppIntegration.tsx`
- **Purpose**: WhatsApp connection management UI
- **Features**: QR code display, status monitoring

#### `/Front_end/project/src/components/WhatsApp/WhatsAppQR.tsx`
- **Purpose**: QR code display component

### Pages Directory

#### `/Front_end/project/src/pages/Admin/Dashboard.tsx`
- **Purpose**: Admin overview dashboard
- **Features**: Stats, restaurant management

#### `/Front_end/project/src/pages/Admin/CreateRestaurant.tsx`
- **Purpose**: New restaurant registration form

#### `/Front_end/project/src/pages/Admin/EditRestaurant.tsx`
- **Purpose**: Edit existing restaurant

#### `/Front_end/project/src/pages/Admin/RestaurantList.tsx`
- **Purpose**: List all restaurants with actions

#### `/Front_end/project/src/pages/Auth/LoginPage.tsx`
- **Purpose**: Login page with form
- **Features**: Role selection, remember me

#### `/Front_end/project/src/pages/Chat/ChatPage.tsx`
- **Purpose**: Public chat interface wrapper
- **URL Params**: `restaurant_id`, `table_id`

#### `/Front_end/project/src/pages/Owner/OwnerDashboard.tsx`
- **Purpose**: Restaurant owner home page
- **Tabs**:
  - Overview (line 114): Stats and quick actions
  - WhatsApp (line 288): Integration settings
- **Quick Actions** (line 135-241):
  - Edit restaurant info
  - Customer conversations
  - Chat logs
  - Create staff
  - Test chat interface

#### `/Front_end/project/src/pages/Owner/ChatLogs.tsx`
- **Purpose**: Legacy chat log view
- **Features**: Simple message list

#### `/Front_end/project/src/pages/Owner/GroupedChatLogs.tsx`
- **Purpose**: Modern chat management interface
- **Features**:
  - Client list with latest messages
  - AI toggle per client
  - Full conversation view
  - Manual messaging

#### `/Front_end/project/src/pages/Owner/CreateStaff.tsx`
- **Purpose**: Staff account creation form

#### `/Front_end/project/src/pages/Owner/OwnerEditRestaurant.tsx`
- **Purpose**: Restaurant profile editing

### Services Directory

#### `/Front_end/project/src/services/api.ts`
- **Purpose**: Main API service layer
- **Key Methods**:
  - Authentication (line 103-131): login, refreshToken
  - Restaurant (line 194-413): CRUD operations
  - Chat (line 449-615): Logs, messages, AI toggle
  - WhatsApp (line 617-675): Status, connect, disconnect
- **Configuration**:
  - Uses axios client from `axiosClient.ts`
  - Fallback to mock data when offline

#### `/Front_end/project/src/services/liveApi.js`
- **Purpose**: Real-time chat API service
- **Methods**:
  - `sendMessage()`: Send chat message
  - `healthCheck()`: Check backend status

### API Client Configuration

#### `/Front_end/project/src/api/axiosClient.ts`
- **Purpose**: Axios instance configuration
- **Features**:
  - Base URL configuration
  - Request/response interceptors
  - Token refresh logic
  - Error handling

### Utils Directory

#### `/Front_end/project/src/utils/ClientSession.js`
- **Purpose**: Client ID generation and management
- **Function**: `getClientId()` - Generate unique client ID

#### `/Front_end/project/src/utils/restaurantUtils.ts`
- **Purpose**: Data transformation utilities
- **Functions**:
  - `transformRestaurantFormData()`: Form to API format
  - `transformApiResponseToFormData()`: API to form format

### Type Definitions

#### `/Front_end/project/src/types/auth.ts`
- **Types**: User, AuthResponse interfaces

#### `/Front_end/project/src/types/restaurant.ts`
- **Types**: Restaurant, Menu, FAQ interfaces

## Quick Reference - Where to Edit What

### To Add New API Endpoint
1. Create route in `/BackEnd/routes/` appropriate file
2. Add schema in `/BackEnd/schemas/` if needed
3. Include router in `/BackEnd/main.py`
4. Add service method in `/Front_end/project/src/services/api.ts`

### To Modify Chat Behavior
1. AI logic: `/BackEnd/services/chat_service.py`
2. Message saving: `/BackEnd/routes/chat.py` or `/BackEnd/routes/chats.py`
3. UI updates: `/Front_end/project/src/components/Chat/ChatInterface.tsx`

### To Change Authentication
1. Backend logic: `/BackEnd/auth.py`
2. Login endpoint: `/BackEnd/routes/auth.py`
3. Frontend context: `/Front_end/project/src/contexts/AuthContext.tsx`
4. Axios config: `/Front_end/project/src/api/axiosClient.ts`

### To Update Restaurant Data Structure
1. Model: `/BackEnd/models.py`
2. Schema: `/BackEnd/schemas/restaurant.py`
3. Service: `/BackEnd/services/restaurant_service.py`
4. Frontend types: `/Front_end/project/src/types/restaurant.ts`

### To Modify WhatsApp Integration
1. FastAPI routes: `/BackEnd/routes/whatsapp.py`
2. Service logic: `/BackEnd/services/whatsapp_service.py`
3. Node.js server: `/BackEnd/whatsapp-service/server.js`
4. Frontend UI: `/Front_end/project/src/components/WhatsApp/`

### To Change UI Layout
1. Layouts: `/Front_end/project/src/components/Layout/`
2. Routes: `/Front_end/project/src/App.tsx`
3. Pages: `/Front_end/project/src/pages/`

### To Modify Database
1. Models: `/BackEnd/models.py`
2. Run migrations if using Alembic
3. Update schemas in `/BackEnd/schemas/`

This reference guide provides exact file locations and line numbers for all major functionality, making it easy to locate and modify any part of the system.