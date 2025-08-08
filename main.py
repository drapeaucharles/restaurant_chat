"""
Main FastAPI application with route registration and middleware setup.
Includes automatic WhatsApp service management.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv
import subprocess
import os
import signal
import time
import threading
import sys
import atexit
from contextlib import asynccontextmanager

from database import engine
import models
from routes import auth, restaurant, chat, clients, chats, whatsapp, speech, smartlamp, update_subcategories, restaurant_categories, debug

# Load environment variables
load_dotenv()

# Global variable to store WhatsApp service process
whatsapp_process = None
whatsapp_monitor_thread = None
shutdown_flag = False

def start_whatsapp_service():
    """Start the Node.js WhatsApp service"""
    global whatsapp_process
    
    try:
        # Use absolute paths to avoid issues with working directory
        whatsapp_service_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "whatsapp-service"))
        node_script = os.path.abspath(os.path.join(whatsapp_service_path, "server.js"))
        
        if not os.path.exists(whatsapp_service_path):
            print("⚠️ WhatsApp service directory not found. WhatsApp features will be unavailable.")
            print(f"   Expected path: {whatsapp_service_path}")
            return None
        
        if not os.path.exists(node_script):
            print("⚠️ WhatsApp service script not found. WhatsApp features will be unavailable.")
            print(f"   Expected script: {node_script}")
            return None
        
        print("🚀 Starting WhatsApp service...")
        print(f"   Service path: {whatsapp_service_path}")
        print(f"   Script path: {node_script}")
        
        # Set environment variables for the WhatsApp service
        env = os.environ.copy()
        env.update({
            "WHATSAPP_PORT": "8002",
            "FASTAPI_URL": os.getenv("PUBLIC_API_URL", "http://localhost:8000"),
            "NODE_ENV": "production",
            # Railway-specific optimizations for WebSocket connections
            "WA_FORCE_NEW_SESSION": "false",
            "WA_DISABLE_SPINS": "true"
        })
        
        # Start the Node.js service with absolute path
        try:
            whatsapp_process = subprocess.Popen(
                ["node", node_script],
                cwd=whatsapp_service_path,
                env=env,
                stdout=sys.stdout,   # ✅ log WhatsApp stdout in console
                stderr=sys.stderr,   # ✅ log WhatsApp stderr in console
                preexec_fn=os.setsid if os.name != 'nt' else None
            )

            
            print(f"✅ WhatsApp service started with PID: {whatsapp_process.pid}")
            
        except FileNotFoundError as e:
            print(f"❌ Node.js not found. Please ensure Node.js is installed and in PATH.")
            print(f"   Error: {str(e)}")
            return None
        except PermissionError as e:
            print(f"❌ Permission denied starting WhatsApp service.")
            print(f"   Error: {str(e)}")
            return None
        except Exception as e:
            print(f"❌ Failed to start WhatsApp service process: {str(e)}")
            return None
        
        # Give it a moment to start
        time.sleep(3)
        
        # Check if process is still running
        if whatsapp_process.poll() is None:
            print("✅ WhatsApp service is running successfully")
        
        return whatsapp_process
        
    except Exception as e:
        print(f"❌ Unexpected error starting WhatsApp service: {str(e)}")
        print(f"   Error type: {type(e).__name__}")
        return None

def stop_whatsapp_service():
    """Stop the WhatsApp service"""
    global whatsapp_process, shutdown_flag
    
    shutdown_flag = True
    
    if whatsapp_process:
        try:
            print("🛑 Stopping WhatsApp service...")
            
            if os.name != 'nt':
                # Unix-like systems
                os.killpg(os.getpgid(whatsapp_process.pid), signal.SIGTERM)
            else:
                # Windows
                whatsapp_process.terminate()
            
            # Wait for graceful shutdown
            try:
                whatsapp_process.wait(timeout=10)
                print("✅ WhatsApp service stopped gracefully")
            except subprocess.TimeoutExpired:
                print("⚠️ WhatsApp service didn't stop gracefully, forcing termination")
                if os.name != 'nt':
                    os.killpg(os.getpgid(whatsapp_process.pid), signal.SIGKILL)
                else:
                    whatsapp_process.kill()
                whatsapp_process.wait()
                print("✅ WhatsApp service terminated")
                
        except Exception as e:
            print(f"❌ Error stopping WhatsApp service: {str(e)}")
        finally:
            whatsapp_process = None

def monitor_whatsapp_service():
    """Monitor WhatsApp service and restart if it crashes"""
    global whatsapp_process, shutdown_flag
    
    while not shutdown_flag:
        try:
            if whatsapp_process and whatsapp_process.poll() is not None:
                print("⚠️ WhatsApp service crashed, restarting...")
                whatsapp_process = start_whatsapp_service()
                
            time.sleep(5)  # Check every 5 seconds
            
        except Exception as e:
            print(f"❌ Error in WhatsApp service monitor: {str(e)}")
            time.sleep(10)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan context manager for startup and shutdown events"""
    global whatsapp_monitor_thread
    
    # Startup
    print("🔄 FastAPI starting up...")
    
    # Start WhatsApp service
    start_whatsapp_service()
    
    # Start monitoring thread
    if whatsapp_process:
        whatsapp_monitor_thread = threading.Thread(target=monitor_whatsapp_service, daemon=True)
        whatsapp_monitor_thread.start()
        print("✅ WhatsApp service monitor started")
    
    print("✅ FastAPI startup complete")
    
    yield
    
    # Shutdown
    print("🔄 FastAPI shutting down...")
    stop_whatsapp_service()
    print("✅ FastAPI shutdown complete")

# Create database tables
models.Base.metadata.create_all(bind=engine)

# Initialize FastAPI app with lifespan management
app = FastAPI(
    title="Restaurant Management API",
    description="API for managing restaurants, clients, and chat interactions with WhatsApp integration",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware - PRODUCTION READY
app.add_middleware(
    CORSMiddleware,
    allow_origins=[        "https://lucky-lokum-06b2de.netlify.app",
        "https://restaurantfront-production.up.railway.app"],  # ✅ VERIFIED: Production domain only# ✅ VERIFIED: Production domain only
    allow_credentials=True,  # ✅ VERIFIED: Required for authentication
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],  # ✅ VERIFIED: Specific methods only
    allow_headers=["*"],
)

# Mount static files for uploads
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# Include routers with proper prefixes to avoid conflicts
app.include_router(auth.router)
app.include_router(restaurant.router)
app.include_router(chat.router)  # No prefix - handles /chat, /client/create-or-update
app.include_router(clients.router)  # New client management router
app.include_router(chats.router, prefix="/chat")  # Prefix for chat management - handles /chat/logs/*, /chat/
app.include_router(whatsapp.router)  # WhatsApp integration routes
app.include_router(speech.router)  # Speech-to-text routes
app.include_router(smartlamp.router)  # Smart Lamp audio routes
app.include_router(update_subcategories.router)  # Admin endpoint for subcategory updates
app.include_router(restaurant_categories.router)  # Restaurant categories endpoint
app.include_router(debug.router)  # Debug endpoints

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
    return {"status": "healthy", "version": "1.0.1"}

@app.get("/whatsapp/service/status")
def whatsapp_service_status():
    """Check WhatsApp service status."""
    global whatsapp_process
    
    if whatsapp_process and whatsapp_process.poll() is None:
        return {
            "status": "running",
            "pid": whatsapp_process.pid,
            "message": "WhatsApp service is running"
        }
    else:
        return {
            "status": "stopped",
            "pid": None,
            "message": "WhatsApp service is not running"
        }

# Register cleanup function
atexit.register(stop_whatsapp_service)

