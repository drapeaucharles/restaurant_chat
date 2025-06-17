#!/bin/bash

# WhatsApp Service Startup Script
# This script starts the Node.js WhatsApp service

echo "🚀 Starting WhatsApp Service..."

# Set environment variables
export WHATSAPP_PORT=8002
export FASTAPI_URL=http://localhost:8000

# Change to service directory
cd "$(dirname "$0")"

# Create sessions directory if it doesn't exist
mkdir -p sessions

# Start the service
echo "📡 Starting on port $WHATSAPP_PORT"
echo "🔗 FastAPI URL: $FASTAPI_URL"

node server.js

