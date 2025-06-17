#!/bin/bash

# WhatsApp Service Startup Script for Railway
# This script starts the Node.js WhatsApp service with Railway-compatible settings

echo "🚀 Starting WhatsApp Service for Railway..."

# Set Railway-compatible environment variables
export WHATSAPP_PORT=${PORT:-8002}
export FASTAPI_URL=${FASTAPI_URL:-http://localhost:8000}

# DO NOT SET CHROME_PATH - let wppconnect handle browser internally
# export CHROME_PATH=${CHROME_PATH:-/usr/bin/google-chrome}

# Change to service directory
cd "$(dirname "$0")"

# Create sessions directory if it doesn't exist
mkdir -p sessions
mkdir -p qr-codes

# Start the service
echo "📡 Starting on port $WHATSAPP_PORT"
echo "🔗 FastAPI URL: $FASTAPI_URL"
echo "🚫 NO Chrome path set - using internal browser handling"

node server.js

