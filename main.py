"""
Main FastAPI application with route registration and middleware setup.
"""

from fastapi import FastAPI

from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from database import engine
import models
from routes import auth, restaurant, chat, clients, chats

# Load environment variables
load_dotenv()

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app
app = FastAPI(
    title="Restaurant Management API",
    description="API for managing restaurants, clients, and chat interactions",
    version="1.0.0"
)


# CORS middleware - PRODUCTION READY
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://lucky-lokum-06b2de.netlify.app"],  # ✅ VERIFIED: Production domain only
    allow_credentials=True,  # ✅ VERIFIED: Required for authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ VERIFIED: Specific methods only
    allow_headers=["*"],
)

# Include routers with proper prefixes to avoid conflicts
app.include_router(auth.router)
app.include_router(restaurant.router)
app.include_router(chat.router)  # No prefix - handles /chat, /client/create-or-update
app.include_router(clients.router)  # New client management router
app.include_router(chats.router, prefix="/chat")  # Prefix for chat management - handles /chat/logs/*, /chat/


# Health check endpoints
@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Restaurant Management API", "status": "running"}

@app.get("/healthcheck")
def healthcheck():
    """Health check endpoint."""
    return {"status": "ok"}
    
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}

