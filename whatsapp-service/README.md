# WhatsApp Baileys Service - Clean Package

## 🚀 Quick Start

1. **Install Dependencies**:
   ```bash
   npm install
   ```

2. **Start Service**:
   ```bash
   npm start
   # or
   node server.js
   ```

3. **Environment Variables** (optional):
   ```bash
   export WHATSAPP_PORT=8002
   export FASTAPI_URL=http://localhost:8000
   export WHATSAPP_API_KEY=supersecretkey123
   ```

## 📁 Package Contents

- `server.js` - Main Baileys service with connection fixes
- `package.json` - Dependencies and scripts
- `sessions/` - Directory for session auth storage
- `qr-codes/` - Directory for QR code storage
- `README.md` - This file

## ✅ Features

- ✅ 100% Browser-free (no Puppeteer/Chrome)
- ✅ Railway deployment compatible
- ✅ Fixed "Connection closed before QR generation" issue
- ✅ Session persistence
- ✅ QR code generation and serving
- ✅ Message sending/receiving
- ✅ FastAPI integration

## 🔧 API Endpoints

- `POST /session/create` - Create new session
- `GET /session/:id/qr` - Get QR code
- `GET /session/:id/status` - Check session status
- `POST /message/send` - Send message
- `DELETE /session/:id` - Delete session
- `GET /health` - Health check

## 📦 Dependencies

All dependencies will be installed via `npm install`:
- @whiskeysockets/baileys (WhatsApp library)
- express (Web server)
- cors (Cross-origin requests)
- axios (HTTP client)
- fs-extra (File system utilities)
- qrcode (QR code generation)

## 🚀 Deployment

Ready for deployment to Railway, Heroku, or any Node.js hosting platform.

No additional configuration needed!

