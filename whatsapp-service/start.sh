#!/bin/bash

# WhatsApp Service Startup Script for Railway using WPPConnect
# No Puppeteer/Chrome needed

echo "🚀 Starting WhatsApp Service for Railway (WPPConnect - WebSocket Only)..."

# Set environment variables (with fallback)
export WHATSAPP_PORT=${PORT:-8002}
export FASTAPI_URL=${FASTAPI_URL:-http://localhost:8000}
export WHATSAPP_API_KEY=${WHATSAPP_API_KEY:-supersecretkey123}

# Change to service directory
cd "$(dirname "$0")"

# Ensure necessary folders exist
mkdir -p sessions

# Start the service
echo "📡 Starting on port $WHATSAPP_PORT"
echo "🔗 FastAPI URL: $FASTAPI_URL"
echo "🔐 API Key (first 5 chars): ${WHATSAPP_API_KEY:0:5}..."

node server.js
