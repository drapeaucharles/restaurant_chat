/**
 * WhatsApp Service using Baileys - COMPLETELY FIXED IMPLEMENTATION
 * 
 * This implementation properly handles the WhatsApp forced disconnect after QR scan
 * and implements correct session management according to official Baileys documentation.
 * 
 * Key fixes:
 * 1. Proper handling of forced disconnect after QR scan (this is NORMAL behavior)
 * 2. Correct socket recreation after forced disconnect
 * 3. Efficient auth state management (not using deprecated useMultiFileAuthState)
 * 4. Proper session cleanup and refresh mechanisms
 * 5. Correct connection state tracking
 */

const { makeWASocket, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');
const QRCode = require('qrcode');
const crypto = require('crypto');

// Ensure crypto is available globally for Baileys
if (typeof global !== 'undefined') {
    global.crypto = crypto;
}

// Configuration
const PORT = process.env.WHATSAPP_PORT || 8002;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const SESSIONS_DIR = path.join(__dirname, 'sessions');
const SHARED_SECRET = process.env.WHATSAPP_SECRET || 'default-secret-change-in-production';
const WHATSAPP_API_KEY = process.env.WHATSAPP_API_KEY || 'supersecretkey123';

// Ensure directories exist
fs.ensureDirSync(SESSIONS_DIR);

// Express app for API endpoints
const app = express();
app.use(cors());
app.use(express.json());

// Store active sessions
const sessions = new Map();

/**
 * Efficient Auth State Implementation
 * Replaces the deprecated useMultiFileAuthState with proper production-ready implementation
 */
class EfficientAuthState {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.authDir = path.join(SESSIONS_DIR, sessionId, 'auth_info_baileys');
        this.credsPath = path.join(this.authDir, 'creds.json');
        this.keysPath = path.join(this.authDir, 'keys.json');
        
        // In-memory cache for efficiency
        this.creds = {};
        this.keys = {};
        this.loaded = false;
    }

    async ensureDir() {
        try {
            await fs.ensureDir(this.authDir);
        } catch (error) {
            // Directory already exists
        }
    }

    async loadState() {
        if (this.loaded) {
            return this.getStateObject();
        }

        await this.ensureDir();
        
        try {
            const credsData = await fs.readFile(this.credsPath, 'utf8');
            this.creds = JSON.parse(credsData);
        } catch (error) {
            this.creds = {};
        }

        try {
            const keysData = await fs.readFile(this.keysPath, 'utf8');
            this.keys = JSON.parse(keysData);
        } catch (error) {
            this.keys = {};
        }

        this.loaded = true;
        return this.getStateObject();
    }

    getStateObject() {
        return {
            state: {
                creds: this.creds,
                keys: {
                    get: async (type, ids) => {
                        const data = {};
                        for (const id of ids) {
                            const key = `${type}-${id}`;
                            if (this.keys[key]) {
                                data[id] = this.keys[key];
                            }
                        }
                        return data;
                    },
                    set: async (data) => {
                        for (const [key, value] of Object.entries(data)) {
                            this.keys[key] = value;
                        }
                        // Periodic save to disk (not on every operation for efficiency)
                        this.scheduleSave();
                    }
                }
            },
            saveCreds: async () => {
                await this.saveCredentials();
            }
        };
    }

    async saveCredentials() {
        await this.ensureDir();
        await fs.writeFile(this.credsPath, JSON.stringify(this.creds, null, 2));
        await fs.writeFile(this.keysPath, JSON.stringify(this.keys, null, 2));
    }

    scheduleSave() {
        if (this.saveTimeout) {
            clearTimeout(this.saveTimeout);
        }
        this.saveTimeout = setTimeout(() => {
            this.saveCredentials().catch(console.error);
        }, 1000); // Save after 1 second of inactivity
    }

    async clearState() {
        try {
            await fs.remove(this.authDir);
        } catch (error) {
            // Files don't exist
        }
        this.creds = {};
        this.keys = {};
        this.loaded = false;
    }

    hasAuth() {
        return Object.keys(this.creds).length > 0;
    }
}

/**
 * WhatsApp Session Management Class
 * Properly handles the forced disconnect cycle and socket recreation
 */
class WhatsAppSession {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.socket = null;
        this.qrCode = null;
        this.status = 'disconnected';
        this.authState = new EfficientAuthState(sessionId);
        this.lastSeen = new Date().toISOString();
        this.connectionAttempts = 0;
        this.maxConnectionAttempts = 3;
        this.isConnecting = false;
        this.qrGeneratedAt = null;
        this.connectionPromise = null;
    }

    log(message) {
        console.log(`🔄 [${this.sessionId}] ${message}`);
    }

    async connect() {
        if (this.isConnecting && this.connectionPromise) {
            this.log('Connection already in progress, returning existing promise');
            return this.connectionPromise;
        }

        this.connectionPromise = this._doConnect();
        return this.connectionPromise;
    }

    async _doConnect() {
        this.isConnecting = true;
        this.connectionAttempts++;

        try {
            this.log(`Starting connection attempt ${this.connectionAttempts}/${this.maxConnectionAttempts}`);
            
            // Load auth state
            const { state, saveCreds } = await this.authState.loadState();
            
            // Get latest Baileys version
            const { version, isLatest } = await fetchLatestBaileysVersion();
            this.log(`Using WA v${version.join('.')}, isLatest: ${isLatest}`);

            // Create socket with optimized configuration
            this.socket = makeWASocket({
                version,
                auth: state,
                printQRInTerminal: false,
                browser: ['Restaurant WhatsApp Bot', 'Desktop', '1.0.0'],
                markOnlineOnConnect: false,
                generateHighQualityLinkPreview: false,
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

            // Return promise that resolves based on connection events
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    this.log('Connection timeout after 60 seconds');
                    this.isConnecting = false;
                    reject(new Error('Connection timeout after 60 seconds'));
                }, 60000);

                const cleanup = () => {
                    clearTimeout(timeout);
                    this.isConnecting = false;
                };

                // Store resolve/reject for use in event handlers
                this.connectionResolve = resolve;
                this.connectionReject = reject;
                this.connectionCleanup = cleanup;
            });

        } catch (error) {
            this.log(`Connection error: ${error.message}`);
            this.isConnecting = false;
            this.connectionPromise = null;
            throw error;
        }
    }

    setupEventHandlers(saveCreds) {
        // Handle credential updates
        this.socket.ev.on('creds.update', async () => {
            this.log('Credentials updated, saving...');
            await saveCreds();
        });

        // Handle messages (forward to FastAPI)
        this.socket.ev.on('messages.upsert', async (m) => {
            const messages = m.messages;
            for (const message of messages) {
                if (!message.key.fromMe && message.message) {
                    await this.forwardMessageToFastAPI(message);
                }
            }
        });

        // Handle connection updates - THIS IS THE CRITICAL PART
        this.socket.ev.on('connection.update', (update) => {
            this.handleConnectionUpdate(update);
        });
    }

    handleConnectionUpdate(update) {
        const { connection, lastDisconnect, qr } = update;
        
        this.log(`Connection update: ${JSON.stringify({ connection, qr: !!qr })}`);

        // QR Code generated
        if (qr) {
            this.qrCode = qr;
            this.status = 'qr_ready';
            this.qrGeneratedAt = new Date();
            this.lastSeen = new Date().toISOString();
            this.log('QR code generated and ready for scanning');
            
            // Resolve immediately when QR is ready (don't wait for full connection)
            if (this.connectionResolve) {
                this.connectionCleanup();
                this.connectionResolve({ 
                    success: true, 
                    status: 'qr_ready', 
                    qr_available: true 
                });
                this.connectionResolve = null;
            }
        }

        // Connection states
        if (connection === 'connecting') {
            this.status = 'connecting';
            this.lastSeen = new Date().toISOString();
            this.log('Connecting to WhatsApp...');
        }

        if (connection === 'open') {
            this.status = 'connected';
            this.lastSeen = new Date().toISOString();
            this.connectionAttempts = 0;
            this.log('✅ Successfully connected to WhatsApp!');
            
            // Resolve if still waiting for connection
            if (this.connectionResolve) {
                this.connectionCleanup();
                this.connectionResolve({ 
                    success: true, 
                    status: 'connected', 
                    connected: true 
                });
                this.connectionResolve = null;
            }
        }

        if (connection === 'close') {
            this.handleConnectionClose(lastDisconnect);
        }
    }

    handleConnectionClose(lastDisconnect) {
        const reason = lastDisconnect?.error?.output?.statusCode;
        this.log(`Connection closed. Reason: ${reason} (${DisconnectReason[reason] || 'unknown'})`);

        // Handle different disconnect reasons
        if (reason === DisconnectReason.loggedOut) {
            this.log('Logged out - clearing auth state');
            this.status = 'logged_out';
            this.authState.clearState();
            
            if (this.connectionReject) {
                this.connectionCleanup();
                this.connectionReject(new Error('Logged out'));
                this.connectionReject = null;
            }
            return;
        }

        // CRITICAL: Handle forced disconnect after QR scan
        if (reason === DisconnectReason.restartRequired || 
            reason === DisconnectReason.connectionReplaced ||
            lastDisconnect?.error?.message?.includes('conflict')) {
            
            this.log('🔄 FORCED DISCONNECT DETECTED - This is normal after QR scan!');
            this.status = 'reconnecting';
            
            // Wait a moment then create new socket with saved credentials
            setTimeout(() => {
                this.log('Creating new socket after forced disconnect...');
                this.socket = null;
                this.isConnecting = false;
                this.connectionPromise = null;
                
                // Attempt reconnection with saved credentials
                this._doConnect().then(() => {
                    this.log('✅ Reconnection successful after forced disconnect');
                }).catch((error) => {
                    this.log(`❌ Reconnection failed: ${error.message}`);
                    this.status = 'connection_failed';
                });
            }, 2000);
            return;
        }

        // Handle other connection failures
        const shouldReconnect = reason !== DisconnectReason.loggedOut && 
                               this.connectionAttempts < this.maxConnectionAttempts;

        if (shouldReconnect) {
            this.log(`Attempting reconnection (${this.connectionAttempts}/${this.maxConnectionAttempts})`);
            this.status = 'reconnecting';
            
            setTimeout(() => {
                this.socket = null;
                this.isConnecting = false;
                this.connectionPromise = null;
                this._doConnect().catch((error) => {
                    this.log(`Reconnection failed: ${error.message}`);
                    this.status = 'connection_failed';
                });
            }, 5000);
        } else {
            this.log('Max reconnection attempts reached or permanent failure');
            this.status = 'connection_failed';
            this.socket = null;
            this.isConnecting = false;
            this.connectionPromise = null;
            
            if (this.connectionReject) {
                this.connectionCleanup();
                this.connectionReject(new Error('Connection failed permanently'));
                this.connectionReject = null;
            }
        }
    }

    async forwardMessageToFastAPI(message) {
        try {
            const response = await axios.post(`${FASTAPI_URL}/whatsapp/incoming`, {
                session_id: this.sessionId,
                message: message,
                timestamp: new Date().toISOString()
            });

            if (response.status !== 200) {
                this.log(`Failed to forward message to FastAPI: ${response.status}`);
            }
        } catch (error) {
            this.log(`Error forwarding message: ${error.message}`);
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
            this.log(`Error sending message: ${error.message}`);
            throw error;
        }
    }

    async getQRCode() {
        if (!this.qrCode) {
            return null;
        }

        // Check if QR code is expired (typically 20-30 seconds)
        if (this.qrGeneratedAt) {
            const ageInSeconds = (new Date() - this.qrGeneratedAt) / 1000;
            if (ageInSeconds > 30) {
                this.log('QR code expired, generating new one...');
                return null;
            }
        }

        try {
            const qrImage = await QRCode.toDataURL(this.qrCode);
            return qrImage;
        } catch (error) {
            this.log(`Error generating QR image: ${error.message}`);
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
            has_auth: this.authState.hasAuth(),
            connection_attempts: this.connectionAttempts
        };
    }

    async cleanup() {
        this.log('Cleaning up session');
        
        if (this.socket) {
            try {
                this.socket.end();
            } catch (error) {
                // Socket already closed
            }
            this.socket = null;
        }
        
        this.qrCode = null;
        this.status = 'disconnected';
        this.isConnecting = false;
        this.connectionPromise = null;
        this.connectionAttempts = 0;
        
        // Clear auth state
        await this.authState.clearState();
    }

    async forceNew() {
        this.log('Forcing new session creation');
        await this.cleanup();
        return this.connect();
    }
}

/**
 * Authentication middleware
 */
function authenticateRequest(req, res, next) {
    const authHeader = req.headers.authorization;
    const apiKey = req.headers['x-api-key'];
    const providedSecret = req.body.secret || req.query.secret;
    
    // Check for valid authentication
    if (apiKey === WHATSAPP_API_KEY || 
        providedSecret === SHARED_SECRET ||
        authHeader === `Bearer ${SHARED_SECRET}`) {
        next();
    } else {
        res.status(401).json({ 
            success: false, 
            error: 'Unauthorized: Invalid API key or secret' 
        });
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
        service: 'WhatsApp Baileys Service - FIXED VERSION'
    });
});

/**
 * Create WhatsApp session for a restaurant
 * Supports both session_id and restaurant_id for backward compatibility
 */
app.post('/session/create', authenticateRequest, async (req, res) => {
    try {
        // Support both session_id and restaurant_id for backward compatibility
        const sessionId = req.body.session_id || req.body.restaurant_id;
        const { force_new = false } = req.body;

        if (!sessionId) {
            return res.status(400).json({ 
                success: false, 
                error: 'session_id or restaurant_id is required' 
            });
        }

        console.log(`📝 [${sessionId}] Creating session (force_new: ${force_new})`);

        let session = sessions.get(sessionId);

        if (force_new && session) {
            await session.cleanup();
            sessions.delete(sessionId);
            session = null;
        }

        if (!session) {
            session = new WhatsAppSession(sessionId);
            sessions.set(sessionId, session);
        }

        const result = await session.connect();
        res.json({
            success: true,
            session_id: sessionId,
            restaurant_id: sessionId, // For backward compatibility
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
 * Get QR code for a restaurant session
 * Supports both :sessionId and :restaurant_id URL parameters
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
                has_auth: session.authState.hasAuth(),
                qr_expired: true,
                status: session.status
            });
        }

        res.json({
            success: true,
            qr_code: qrImage,
            status: session.status,
            session_id: sessionId,
            restaurant_id: sessionId // For backward compatibility
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
 * Get session status for a restaurant
 * Supports both :sessionId and :restaurant_id URL parameters
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
 * Send message via WhatsApp
 * Supports both session_id and restaurant_id for backward compatibility
 */
app.post('/message/send', authenticateRequest, async (req, res) => {
    try {
        // Support both session_id and restaurant_id for backward compatibility
        const sessionId = req.body.session_id || req.body.restaurant_id;
        const { to, message } = req.body;

        if (!sessionId || !to || !message) {
            return res.status(400).json({ 
                success: false, 
                error: 'session_id (or restaurant_id), to, and message are required' 
            });
        }

        const session = sessions.get(sessionId);
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
 * Delete session for a restaurant
 * Supports both :sessionId and :restaurant_id URL parameters
 */
app.delete('/session/:sessionId', authenticateRequest, async (req, res) => {
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

// Legacy endpoints for backward compatibility
app.post('/restaurant/:restaurant_id/connect', authenticateRequest, async (req, res) => {
    req.body.restaurant_id = req.params.restaurant_id;
    return app._router.handle(Object.assign(req, { method: 'POST', url: '/session/create' }), res);
});

app.get('/restaurant/:restaurant_id/qr', async (req, res) => {
    req.params.restaurant_id = req.params.restaurant_id;
    return app._router.handle(Object.assign(req, { method: 'GET', url: `/session/${req.params.restaurant_id}/qr` }), res);
});

app.get('/restaurant/:restaurant_id/status', async (req, res) => {
    req.params.restaurant_id = req.params.restaurant_id;
    return app._router.handle(Object.assign(req, { method: 'GET', url: `/session/${req.params.restaurant_id}/status` }), res);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`🚀 WhatsApp Baileys Service running on port ${PORT}`);
    console.log(`📱 Service ready to handle WhatsApp connections`);
    console.log(`🔗 FastAPI URL: ${FASTAPI_URL}`);
    console.log(`📁 Sessions directory: ${SESSIONS_DIR}`);
    console.log(`🔑 Using API key: ${WHATSAPP_API_KEY.substring(0, 10)}...`);
    console.log(`🚫 NO Puppeteer, NO Chromium, NO browser dependencies!`);
    console.log(`⚡ Powered by Baileys WebSocket protocol`);
    console.log(`🌐 Node version: ${process.version}`);
    
    // Log existing sessions
    const existingSessions = fs.readdirSync(SESSIONS_DIR).filter(dir => 
        fs.statSync(path.join(SESSIONS_DIR, dir)).isDirectory()
    );
    console.log(`💾 Found ${existingSessions.length} existing session directories`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Shutting down gracefully...');
    
    // Cleanup all sessions
    for (const [sessionId, session] of sessions) {
        console.log(`🧹 Cleaning up session: ${sessionId}`);
        await session.cleanup();
    }
    
    process.exit(0);
});

module.exports = app;

