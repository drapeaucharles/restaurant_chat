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
from routes import auth, restaurant, chat_dynamic, clients, chats, whatsapp, speech, smartlamp, update_subcategories, restaurant_categories, debug, version, embeddings, migration, db_management, embeddings_admin, redis_check, memory_debug, diagnostic, businesses, businesses_secure

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
# IMPORTANT: Order matters! Enhanced chat must come before chats to take precedence
app.include_router(auth.router)
app.include_router(restaurant.router)
app.include_router(chat_dynamic.router)  # Dynamic chat with restaurant-specific AI mode - handles /chat
app.include_router(clients.router)  # New client management router
app.include_router(chats.router, prefix="/chat")  # Chat management - handles /chat/logs/*, etc
app.include_router(whatsapp.router)  # WhatsApp integration routes
app.include_router(speech.router)  # Speech-to-text routes
app.include_router(smartlamp.router)  # Smart Lamp audio routes
app.include_router(update_subcategories.router)  # Admin endpoint for subcategory updates
app.include_router(restaurant_categories.router)  # Restaurant categories endpoint
app.include_router(debug.router)  # Debug endpoints
app.include_router(version.router)  # Version endpoint
app.include_router(embeddings.router)  # RAG embeddings endpoints
app.include_router(embeddings_admin.router)  # Embeddings admin endpoints
app.include_router(migration.router)  # Migration endpoints
app.include_router(db_management.router)  # Database management endpoints
app.include_router(redis_check.router)  # Redis check endpoint
app.include_router(memory_debug.router)  # Memory debug endpoint
app.include_router(diagnostic.router)  # Comprehensive diagnostic endpoint
app.include_router(businesses.router)  # Business discovery endpoints
app.include_router(businesses_secure.router)  # Secure business management with permissions

# Admin management endpoints
from routes import admin_management
app.include_router(admin_management.router)  # Admin management endpoints

# Simple admin endpoints
from routes import simple_admin
app.include_router(simple_admin.router)  # Simple admin endpoints

# Complete admin delete endpoints
from routes import complete_admin_delete
app.include_router(complete_admin_delete.router)  # Complete admin delete

# Health check endpoints
@app.get("/")
def root():
    """Root endpoint with deployment info."""
    import subprocess
    try:
        commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()[:8]
        branch = subprocess.check_output(['git', 'rev-parse', '--abbrev-ref', 'HEAD'], text=True).strip()
    except:
        commit = "unknown"
        branch = "unknown"
    
    return {
        "message": "Restaurant Management API",
        "status": "running",
        "deployment": {
            "branch": branch,
            "commit": commit,
            "version": "v7-rag-lightweight-READY",
            "has_pasta_fixes": True,
            "mia_chat_service": "rag_enhanced_lightweight",
            "deployment_timestamp": "2025-01-14-2000",
            "features": ["lightweight_rag", "huggingface_api", "maria_personality", "redis_caching", "vector_embeddings", "no_ml_libs"],
            "latest_addition": "lightweight_embeddings_api",
            "notes": {
                "redis": "Connected and working",
                "rag": "Using HuggingFace API - add HUGGINGFACE_API_KEY",
                "setup": "See HUGGINGFACE_SETUP.md for API key"
            }
        }
    }

@app.get("/healthcheck")
def healthcheck():
    """Health check endpoint."""
    return {"status": "ok"}
    
@app.get("/health")
def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.1"}

@app.get("/debug/test-chat-import")
def test_chat_import():
    """Test importing the improved chat service."""
    results = {}
    
    # Test importing improved service
    try:
        from services.mia_chat_service_improved import mia_chat_service
        results["import_improved"] = "SUCCESS"
        
        # Check if it has the right attributes
        import inspect
        results["improved_source_file"] = inspect.getfile(mia_chat_service)
        results["improved_function_name"] = mia_chat_service.__name__
    except Exception as e:
        results["import_improved"] = f"FAILED: {str(e)}"
    
    # Test importing regular MIA service
    try:
        from services.mia_chat_service import mia_chat_service as regular_mia
        results["import_regular_mia"] = "SUCCESS"
    except Exception as e:
        results["import_regular_mia"] = f"FAILED: {str(e)}"
    
    # Test chat route flag
    try:
        from routes.chat import USE_IMPROVED_CHAT
        results["USE_IMPROVED_CHAT"] = USE_IMPROVED_CHAT
    except Exception as e:
        results["USE_IMPROVED_CHAT"] = f"FAILED: {str(e)}"
    
    return results

@app.get("/debug/chat-config")
def debug_chat_config():
    """Debug endpoint to check chat configuration."""
    import os
    from pathlib import Path
    
    # Check if improved service file exists
    improved_exists = Path("services/mia_chat_service_improved.py").exists()
    
    # Check environment variable
    use_improved = os.getenv("USE_IMPROVED_CHAT", "not_set")
    
    # Import the flag from chat.py
    try:
        from routes.chat import USE_IMPROVED_CHAT
        route_flag = USE_IMPROVED_CHAT
    except:
        route_flag = "import_failed"
    
    return {
        "improved_service_file_exists": improved_exists,
        "USE_IMPROVED_CHAT_env": use_improved,
        "USE_IMPROVED_CHAT_in_route": route_flag,
        "expected_behavior": "Should greet without pasta" if route_flag else "Will show pasta",
        "files_in_services": os.listdir("services") if os.path.exists("services") else "services_dir_not_found"
    }

@app.get("/debug/menu-data/{restaurant_id}")
def debug_menu_data(restaurant_id: str):
    """Debug endpoint to inspect menu categorization"""
    from database import get_db
    db = next(get_db())
    
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        return {"error": "Restaurant not found"}
    
    data = restaurant.data or {}
    menu_items = data.get("menu", [])
    
    # Find risotto and pasta items
    pasta_items = []
    risotto_items = []
    
    for item in menu_items:
        name = item.get('dish') or item.get('name', '')
        subcategory = item.get('subcategory', '')
        
        if 'risotto' in name.lower():
            risotto_items.append({
                "name": name,
                "subcategory": subcategory,
                "ingredients": item.get('ingredients', [])
            })
        
        # Check various pasta types
        pasta_keywords = ['spaghetti', 'penne', 'linguine', 'fettuccine', 'ravioli', 'lasagna', 'gnocchi', 'tagliatelle', 'pappardelle']
        if subcategory == 'pasta' or any(keyword in name.lower() for keyword in pasta_keywords):
            pasta_items.append({
                "name": name,
                "subcategory": subcategory,
                "is_actual_pasta": True
            })
    
    return {
        "total_menu_items": len(menu_items),
        "risotto_items": risotto_items,
        "pasta_subcategory_items": pasta_items,
        "all_subcategories": list(set(item.get('subcategory', 'unknown') for item in menu_items))
    }

@app.post("/debug/test-improved-direct")
def test_improved_direct(message: str = "hello"):
    """Test the improved service directly."""
    from database import get_db
    from schemas.chat import ChatRequest
    
    try:
        from services.mia_chat_service_improved import mia_chat_service
        
        # Create test request
        req = ChatRequest(
            restaurant_id="bella_vista_restaurant",
            client_id="550e8400-e29b-41d4-a716-446655440000",
            sender_type="client",
            message=message
        )
        
        # Get DB session
        db = next(get_db())
        
        # Call improved service
        result = mia_chat_service(req, db)
        
        return {
            "success": True,
            "answer": result.answer,
            "has_pasta": "pasta" in result.answer.lower()
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "type": type(e).__name__
        }

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

