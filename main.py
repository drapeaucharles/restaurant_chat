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


# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(restaurant.router)
app.include_router(chat.router)  # Keep existing chat router for backward compatibility
app.include_router(clients.router)  # New client management router
app.include_router(chats.router)  # New chat management router


# Health check endpoints
@app.get("/")
def root():
    """Root endpoint."""
    return {"message": "Restaurant Management API", "status": "running"}

@app.get("/healthcheck")
def healthcheck():
    return {"status": "ok"}
    
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/test-alive")
def test_alive():
    """Test endpoint to verify API is alive."""
    return {"ok": True}


@app.get("/debug/routes")
def list_routes():
    """Debug endpoint to list all available routes."""
    return [{"path": route.path, "methods": route.methods} for route in app.routes]

