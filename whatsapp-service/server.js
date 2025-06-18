/**
 * WhatsApp Service using Baileys - WORKING VERSION RESTORED
 * Following the configuration that was actually working on Railway
 */

const express = require('express');
const { makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');
const fetch = require('node-fetch');

// Ensure crypto is available globally for Baileys
if (typeof global !== 'undefined') {
    global.crypto = crypto;
}

const app = express();
app.use(express.json());

// CORS middleware
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept, Authorization, x-api-key');
    if (req.method === 'OPTIONS') {
        res.sendStatus(200);
    } else {
        next();
    }
});

// API key middleware
const API_KEY = process.env.WHATSAPP_API_KEY || 'supersecretkey123';
const authenticateApiKey = (req, res, next) => {
    const apiKey = req.headers['x-api-key'];
    if (apiKey && apiKey === API_KEY) {
        return next();
    }
    
    const authHeader = req.headers['authorization'];
    if (authHeader && authHeader.startsWith('Bearer ')) {
        const bearerToken = authHeader.substring(7);
        if (bearerToken === API_KEY) {
            return next();
        }
    }
    
    return res.status(401).json({ success: false, error: 'Invalid API key' });
};

// In-memory session storage
const sessions = new Map();
const SESSIONS_DIR = path.join(__dirname, 'sessions');

// Ensure sessions directory exists
fs.ensureDirSync(SESSIONS_DIR);

/**
 * Session Management Class - SIMPLIFIED WORKING VERSION
 */
class WhatsAppSession {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.socket = null;
        this.qrCode = null;
        this.status = 'disconnected';
        this.connectionPromise = null;
        this.sessionDir = path.join(SESSIONS_DIR, sessionId);
        this.lastSeen = new Date().toISOString();
        this.retryCount = 0;
        this.maxRetries = 3;
    }

    async connect() {
        if (this.connectionPromise) {
            return this.connectionPromise;
        }

        this.connectionPromise = this._doConnect().catch(error => {
            console.error(`❌ [${this.sessionId}] Connection failed:`, error);
            this.connectionPromise = null;
            throw error;
        });
        return this.connectionPromise;
    }

    async _doConnect() {
        try {
            console.log(`🔄 [${this.sessionId}] Starting connection...`);
            
            // Ensure session directory exists
            fs.ensureDirSync(this.sessionDir);
            
            // Load auth state using the WORKING method
            const { state, saveCreds } = await useMultiFileAuthState(this.sessionDir);
            
            // Get latest Baileys version
            const { version, isLatest } = await fetchLatestBaileysVersion();
            console.log(`📱 [${this.sessionId}] Using WA v${version.join('.')}, isLatest: ${isLatest}`);

            // Create socket with WORKING configuration
            this.socket = makeWASocket({
                version,
                auth: state,
                printQRInTerminal: false,
                logger: {
                    level: 'silent',
                    child: () => ({ 
                        level: 'silent',
                        trace: () => {},
                        debug: () => {},
                        info: () => {},
                        warn: () => {},
                        error: () => {},
                        fatal: () => {}
                    }),
                    trace: () => {},
                    debug: () => {},
                    info: () => {},
                    warn: () => {},
                    error: () => {},
                    fatal: () => {}
                },
                browser: ['Restaurant Bot', 'Chrome', '1.0.0'],
                markOnlineOnConnect: false,
                syncFullHistory: false,
                defaultQueryTimeoutMs: 60000,
                connectTimeoutMs: 60000,
                keepAliveIntervalMs: 30000,
                getMessage: async (key) => {
                    return { conversation: 'Hello' };
                }
            });

            // Set up event handlers
            this.setupEventHandlers(saveCreds);

            // Wait for initial connection or QR with 30-second timeout
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Connection timeout after 30 seconds'));
                }, 30000);

                const cleanup = () => {
                    clearTimeout(timeout);
                };

                this.socket.ev.on('connection.update', (update) => {
                    const { connection, lastDisconnect, qr } = update;

                    if (qr) {
                        this.qrCode = qr;
                        this.status = 'qr_ready';
                        this.lastSeen = new Date().toISOString();
                        console.log(`📱 [${this.sessionId}] QR code generated`);
                        cleanup();
                        resolve({ success: true, status: 'qr_ready', qr_available: true });
                    }

                    if (connection === 'open') {
                        this.status = 'connected';
                        this.lastSeen = new Date().toISOString();
                        this.retryCount = 0;
                        console.log(`✅ [${this.sessionId}] Connected successfully`);
                        cleanup();
                        resolve({ success: true, status: 'connected', connected: true });
                    }

                    if (connection === 'close') {
                        const shouldReconnect = (lastDisconnect?.error)?.output?.statusCode !== DisconnectReason.loggedOut;
                        console.log(`❌ [${this.sessionId}] Connection closed. Should reconnect: ${shouldReconnect}`);
                        
                        if (shouldReconnect && this.retryCount < this.maxRetries) {
                            this.retryCount++;
                            console.log(`🔄 [${this.sessionId}] Retrying connection (${this.retryCount}/${this.maxRetries})`);
                            setTimeout(() => this._doConnect(), 5000);
                        } else {
                            this.status = 'connection_failed';
                            this.socket = null;
                            this.connectionPromise = null;
                            cleanup();
                            reject(new Error('Connection failed permanently'));
                        }
                    }
                });
            });

        } catch (error) {
            console.error(`❌ [${this.sessionId}] Connection error:`, error);
            this.connectionPromise = null;
            throw error;
        }
    }

    setupEventHandlers(saveCreds) {
        // Handle credential updates
        this.socket.ev.on('creds.update', saveCreds);

        // Handle messages (forward to FastAPI)
        this.socket.ev.on('messages.upsert', async (m) => {
            try {
                const messages = m.messages;
                for (const message of messages) {
                    if (!message.key.fromMe && message.message) {
                        await this.forwardMessageToFastAPI(message);
                    }
                }
            } catch (error) {
                console.error(`❌ [${this.sessionId}] Error handling messages:`, error);
            }
        });

        // Handle connection updates
        this.socket.ev.on('connection.update', (update) => {
            const { connection, lastDisconnect, qr } = update;
            
            if (qr) {
                this.qrCode = qr;
                this.status = 'qr_ready';
                this.lastSeen = new Date().toISOString();
            }

            if (connection === 'connecting') {
                this.status = 'connecting';
                this.lastSeen = new Date().toISOString();
            }

            if (connection === 'open') {
                this.status = 'connected';
                this.lastSeen = new Date().toISOString();
                this.retryCount = 0;
            }

            if (connection === 'close') {
                const reason = lastDisconnect?.error?.output?.statusCode;
                if (reason === DisconnectReason.loggedOut) {
                    this.status = 'logged_out';
                    this.cleanup();
                } else {
                    this.status = 'connection_failed';
                }
                this.lastSeen = new Date().toISOString();
            }
        });
    }

    async forwardMessageToFastAPI(message) {
        try {
            const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
            const response = await fetch(`${fastApiUrl}/whatsapp/incoming`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    session_id: this.sessionId,
                    message: message,
                    timestamp: new Date().toISOString()
                })
            });

            if (!response.ok) {
                console.error(`❌ [${this.sessionId}] Failed to forward message to FastAPI:`, response.status);
            }
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error forwarding message:`, error);
        }
    }

    async sendMessage(to, message) {
        if (!this.socket || this.status !== 'connected') {
            throw new Error('WhatsApp not connected');
        }

        try {
            const result = await this.socket.sendMessage(to, { text: message });
            return result;
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error sending message:`, error);
            throw error;
        }
    }

    async getQRCode() {
        if (!this.qrCode) {
            return null;
        }

        try {
            const qrImage = await QRCode.toDataURL(this.qrCode);
            return qrImage;
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error generating QR image:`, error);
            return null;
        }
    }

    getStatus() {
        return {
            session_id: this.sessionId,
            status: this.status,
            connected: this.status === 'connected',
            qr_available: !!this.qrCode && this.status === 'qr_ready',
            last_seen: this.lastSeen,
            has_auth: false
        };
    }

    async cleanup() {
        console.log(`🧹 [${this.sessionId}] Cleaning up session`);
        
        try {
            if (this.socket) {
                this.socket.end();
                this.socket = null;
            }
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error during socket cleanup:`, error);
        }
        
        this.qrCode = null;
        this.status = 'disconnected';
        this.connectionPromise = null;
        this.retryCount = 0;
        
        // Clear auth state
        try {
            await fs.remove(this.sessionDir);
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error clearing auth state:`, error);
        }
    }

    async forceNew() {
        await this.cleanup();
        return this.connect();
    }
}

// API Routes

/**
 * Health check endpoint
 */
app.get('/health', (req, res) => {
    res.json({ 
        success: true, 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        active_sessions: sessions.size,
        service: 'whatsapp-baileys',
        port: process.env.WHATSAPP_PORT || 8002
    });
});

/**
 * Create or get session
 */
app.post('/session/create', authenticateApiKey, async (req, res) => {
    try {
        const { session_id, force_new = false } = req.body;

        if (!session_id) {
            return res.status(400).json({ success: false, error: 'session_id is required' });
        }

        console.log(`📝 [${session_id}] Creating session (force_new: ${force_new})`);

        let session = sessions.get(session_id);

        if (force_new && session) {
            await session.cleanup();
            sessions.delete(session_id);
            session = null;
        }

        if (!session) {
            session = new WhatsAppSession(session_id);
            sessions.set(session_id, session);
        }

        const result = await session.connect();
        res.json({
            success: true,
            session_id: session_id,
            status: session.status,
            message: 'Session created successfully. QR code ready for scanning.',
            qr_available: !!session.qrCode
        });

    } catch (error) {
        console.error('❌ Session creation error:', error);
        res.status(500).json({ 
            success: false, 
            error: `Session creation failed: ${error.message}` 
        });
    }
});

/**
 * Start session and generate QR code (URL parameter version)
 * This endpoint is expected by FastAPI for session management
 */
app.post('/session/:id/start', authenticateApiKey, async (req, res) => {
    try {
        const session_id = req.params.id;
        const { force_new = false } = req.body;

        if (!session_id) {
            return res.status(400).json({ success: false, error: 'session_id is required in URL' });
        }

        console.log(`📝 [${session_id}] Starting session via URL parameter (force_new: ${force_new})`);

        let session = sessions.get(session_id);

        if (force_new && session) {
            await session.cleanup();
            sessions.delete(session_id);
            session = null;
        }

        if (!session) {
            session = new WhatsAppSession(session_id);
            sessions.set(session_id, session);
        }

        const result = await session.connect();
        
        // Get QR code if available
        const qrImage = await session.getQRCode();
        
        res.json({
            success: true,
            session_id: session_id,
            status: session.status,
            message: 'Session started successfully. QR code ready for scanning.',
            qr_available: !!session.qrCode,
            qr_code: qrImage, // Include base64 QR code in response
            connected: session.status === 'connected'
        });

    } catch (error) {
        console.error('❌ Session start error:', error);
        res.status(500).json({ 
            success: false, 
            error: `Session start failed: ${error.message}` 
        });
    }
});

/**
 * Get QR code for session
 */
app.get('/session/:sessionId/qr', async (req, res) => {
    try {
        const { sessionId } = req.params;
        const { refresh = false } = req.query;

        const session = sessions.get(sessionId);
        if (!session) {
            return res.status(404).json({ 
                success: false, 
                error: 'Session not found. Please create a session first.',
                status: 'not_found'
            });
        }

        if (refresh === 'true') {
            console.log(`🔄 [${sessionId}] Refreshing QR code`);
            await session.forceNew();
        }

        const qrImage = await session.getQRCode();
        if (!qrImage) {
            return res.status(404).json({ 
                success: false, 
                error: 'QR code not found. Session may not be created, already connected, or expired. Try creating a new session.',
                has_auth: false,
                qr_expired: session.status !== 'qr_ready',
                status: session.status
            });
        }

        res.json({
            success: true,
            qr_code: qrImage,
            status: session.status,
            session_id: sessionId
        });

    } catch (error) {
        console.error('❌ QR fetch error:', error);
        res.status(500).json({ 
            success: false, 
            error: `QR generation failed: ${error.message}` 
        });
    }
});

/**
 * Get session status
 */
app.get('/session/:sessionId/status', (req, res) => {
    try {
        const { sessionId } = req.params;
        const session = sessions.get(sessionId);

        if (!session) {
            return res.json({
                status: 'not_found',
                connected: false,
                message: 'No session found for this restaurant',
                has_auth: false,
                qr_available: false
            });
        }

        res.json(session.getStatus());

    } catch (error) {
        console.error('❌ Status check error:', error);
        res.status(500).json({ 
            success: false, 
            error: `Status check failed: ${error.message}` 
        });
    }
});

/**
 * Send message
 */
app.post('/message/send', authenticateApiKey, async (req, res) => {
    try {
        const { session_id, to, message } = req.body;

        if (!session_id || !to || !message) {
            return res.status(400).json({ 
                success: false, 
                error: 'session_id, to, and message are required' 
            });
        }

        const session = sessions.get(session_id);
        if (!session) {
            return res.status(404).json({ 
                success: false, 
                error: 'Session not found' 
            });
        }

        const result = await session.sendMessage(to, message);
        res.json({
            success: true,
            message: 'Message sent successfully',
            result: result
        });

    } catch (error) {
        console.error('❌ Message send error:', error);
        res.status(500).json({ 
            success: false, 
            error: `Message send failed: ${error.message}` 
        });
    }
});

/**
 * Delete session
 */
app.delete('/session/:sessionId', authenticateApiKey, async (req, res) => {
    try {
        const { sessionId } = req.params;
        const session = sessions.get(sessionId);

        if (session) {
            await session.cleanup();
            sessions.delete(sessionId);
        }

        res.json({
            success: true,
            message: 'Session deleted successfully'
        });

    } catch (error) {
        console.error('❌ Session deletion error:', error);
        res.status(500).json({ 
            success: false, 
            error: `Session deletion failed: ${error.message}` 
        });
    }
});

// Global error handlers to prevent silent crashes
process.on('uncaughtException', (error) => {
    console.error('❌ Uncaught Exception:', error);
    // Don't exit the process, just log the error
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
    // Don't exit the process, just log the error
});

// Start server with proper error handling
const PORT = process.env.WHATSAPP_PORT || process.env.PORT || 8002;
const server = app.listen(PORT, '0.0.0.0', (error) => {
    if (error) {
        console.error('❌ Failed to start WhatsApp service:', error);
        process.exit(1);
    }
    console.log(`✅ Node.js WhatsApp service started on port ${PORT}`);
    console.log(`🚀 WhatsApp Baileys Service running on http://0.0.0.0:${PORT}`);
    console.log(`📱 Service properly configured according to Baileys documentation`);
    console.log(`🔗 Health check available at: http://localhost:${PORT}/health`);
});

// Handle server startup errors
server.on('error', (error) => {
    console.error('❌ Server error:', error);
    if (error.code === 'EADDRINUSE') {
        console.error(`❌ Port ${PORT} is already in use`);
        process.exit(1);
    }
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Shutting down gracefully...');
    
    // Close server first
    server.close(() => {
        console.log('🛑 HTTP server closed');
    });
    
    // Clean up sessions
    for (const [sessionId, session] of sessions) {
        try {
            await session.cleanup();
        } catch (error) {
            console.error(`❌ Error cleaning up session ${sessionId}:`, error);
        }
    }
    
    console.log('🛑 All sessions cleaned up');
    process.exit(0);
});

process.on('SIGTERM', async () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    
    // Close server first
    server.close(() => {
        console.log('🛑 HTTP server closed');
    });
    
    // Clean up sessions
    for (const [sessionId, session] of sessions) {
        try {
            await session.cleanup();
        } catch (error) {
            console.error(`❌ Error cleaning up session ${sessionId}:`, error);
        }
    }
    
    console.log('🛑 All sessions cleaned up');
    process.exit(0);
});

module.exports = app;

