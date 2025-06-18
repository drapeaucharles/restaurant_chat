/**
 * WhatsApp Service using Baileys - WORKING VERSION RESTORED
 * Following the configuration that was actually working on Railway
 */

const express = require('express');
const { makeWASocket, DisconnectReason, fetchLatestBaileysVersion } = require('@whiskeysockets/baileys');
const QRCode = require('qrcode');
const fs = require('fs-extra');
const path = require('path');
const crypto = require('crypto');
const fetch = require('node-fetch');
const { Pool } = require('pg');

// Ensure crypto is available globally for Baileys
if (typeof global !== 'undefined') {
    global.crypto = crypto;
}

const app = express();
app.use(express.json());

// Database connection
const pool = new Pool({
    connectionString: process.env.DATABASE_URL || 'postgresql://postgres:password@localhost:5432/railway',
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

/**
 * Database-backed Auth State for Railway persistence
 * Replaces file-based storage with PostgreSQL storage
 */
class DatabaseAuthState {
    constructor(sessionId) {
        this.sessionId = sessionId;
    }

    async loadState() {
        try {
            console.log(`🔍 [${this.sessionId}] Attempting to load session from database...`);
            
            const client = await pool.connect();
            console.log(`✅ [${this.sessionId}] Database connection established`);
            
            // Try to load existing session from database
            const result = await client.query(
                'SELECT creds, keys FROM whatsapp_sessions WHERE session_id = $1',
                [this.sessionId]
            );
            
            let creds = {};
            let keys = {};
            
            if (result.rows.length > 0) {
                creds = result.rows[0].creds || {};
                keys = result.rows[0].keys || {};
                console.log(`📁 [${this.sessionId}] Loaded existing session from database (${Object.keys(creds).length} creds, ${Object.keys(keys).length} keys)`);
            } else {
                console.log(`📁 [${this.sessionId}] No existing session found, creating new one`);
            }
            
            client.release();
            
            const saveCreds = async () => {
                try {
                    console.log(`💾 [${this.sessionId}] Attempting to save credentials to database...`);
                    const client = await pool.connect();
                    
                    // Upsert session data
                    await client.query(`
                        INSERT INTO whatsapp_sessions (session_id, creds, keys, updated_at) 
                        VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                        ON CONFLICT (session_id) 
                        DO UPDATE SET 
                            creds = EXCLUDED.creds,
                            keys = EXCLUDED.keys,
                            updated_at = CURRENT_TIMESTAMP
                    `, [this.sessionId, JSON.stringify(creds), JSON.stringify(keys)]);
                    
                    client.release();
                    console.log(`✅ [${this.sessionId}] Session saved to database successfully`);
                } catch (error) {
                    console.error(`❌ [${this.sessionId}] Error saving session to database:`, error);
                }
            };
            
            return {
                state: { creds, keys },
                saveCreds
            };
            
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error loading session from database:`, error);
            
            // Fallback to empty state
            console.log(`🔄 [${this.sessionId}] Using fallback empty state`);
            return {
                state: { creds: {}, keys: {} },
                saveCreds: async () => {
                    console.log(`❌ [${this.sessionId}] Fallback saveCreds - database unavailable`);
                }
            };
        }
    }

    async clearState() {
        try {
            const client = await pool.connect();
            await client.query('DELETE FROM whatsapp_sessions WHERE session_id = $1', [this.sessionId]);
            client.release();
            console.log(`🗑️ [${this.sessionId}] Session cleared from database`);
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error clearing session from database:`, error);
        }
    }
}

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

/**
 * Session Management Class - DATABASE-BACKED VERSION
 */
class WhatsAppSession {
    constructor(sessionId) {
        this.sessionId = sessionId;
        this.socket = null;
        this.qrCode = null;
        this.status = 'disconnected';
        this.connectionPromise = null;
        this.authState = new DatabaseAuthState(sessionId);
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
            
            // Load auth state from database
            console.log(`📊 [${this.sessionId}] Loading auth state...`);
            const { state, saveCreds } = await this.authState.loadState();
            
            console.log(`📁 [${this.sessionId}] Auth state loaded from database`);
            console.log(`🔑 [${this.sessionId}] Has existing creds: ${!!state.creds?.noiseKey}`);
            
            // Get latest Baileys version
            console.log(`📱 [${this.sessionId}] Fetching Baileys version...`);
            const { version, isLatest } = await fetchLatestBaileysVersion();
            console.log(`📱 [${this.sessionId}] Using WA v${version.join('.')}, isLatest: ${isLatest}`);

            // Create socket with WORKING configuration
            console.log(`🔌 [${this.sessionId}] Creating WhatsApp socket...`);
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
            console.log(`✅ [${this.sessionId}] WhatsApp socket created successfully`);

            // Set up event handlers
            console.log(`🎧 [${this.sessionId}] Setting up event handlers...`);
            this.setupEventHandlers(saveCreds);

            // Wait for initial connection or QR with 60-second timeout (increased)
            console.log(`⏳ [${this.sessionId}] Waiting for connection or QR code...`);
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    console.log(`⏰ [${this.sessionId}] Connection timeout reached`);
                    reject(new Error('Connection timeout after 60 seconds'));
                }, 60000); // Increased to 60 seconds

                const cleanup = () => {
                    clearTimeout(timeout);
                };

                this.socket.ev.on('connection.update', (update) => {
                    const { connection, lastDisconnect, qr } = update;
                    console.log(`🔄 [${this.sessionId}] Connection update: connection=${connection}, qr=${!!qr}`);

                    if (qr) {
                        this.qrCode = qr;
                        this.status = 'qr_ready';
                        this.lastSeen = new Date().toISOString();
                        console.log(`📱 [${this.sessionId}] QR code generated successfully`);
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
        // Handle credential updates with debugging
        this.socket.ev.on('creds.update', async () => {
            try {
                console.log(`💾 [${this.sessionId}] Saving credentials...`);
                await saveCreds();
                console.log(`✅ [${this.sessionId}] Credentials saved successfully`);
            } catch (error) {
                console.error(`❌ [${this.sessionId}] Error saving credentials:`, error);
            }
        });

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
            // Extract phone number from Baileys message
            const fromNumber = message.key.remoteJid?.replace('@s.whatsapp.net', '') || 'unknown';
            
            // Extract message text from Baileys message object
            let messageText = '';
            if (message.message?.conversation) {
                messageText = message.message.conversation;
            } else if (message.message?.extendedTextMessage?.text) {
                messageText = message.message.extendedTextMessage.text;
            } else if (message.message?.imageMessage?.caption) {
                messageText = message.message.imageMessage.caption;
            } else {
                messageText = 'Media message or unsupported message type';
            }

            const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
            const response = await fetch(`${fastApiUrl}/whatsapp/incoming`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    from_number: fromNumber,
                    message: messageText,
                    session_id: this.sessionId,
                    message_id: message.key.id,
                    timestamp: new Date().toISOString(),
                    chat_id: message.key.remoteJid
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ [${this.sessionId}] Failed to forward message to FastAPI:`, response.status, errorText);
            } else {
                console.log(`✅ [${this.sessionId}] Message forwarded successfully to FastAPI`);
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
            // Format phone number as WhatsApp JID
            let jid = to;
            
            // If it's just a phone number, convert to WhatsApp JID format
            if (!to.includes('@')) {
                // Remove any non-digit characters
                const cleanNumber = to.replace(/\D/g, '');
                
                // Add country code if missing (assuming US +1 if 10 digits)
                let formattedNumber = cleanNumber;
                if (cleanNumber.length === 10) {
                    formattedNumber = '1' + cleanNumber;
                }
                
                // Format as WhatsApp JID
                jid = formattedNumber + '@s.whatsapp.net';
            }
            
            console.log(`📱 [${this.sessionId}] Sending to JID: ${jid}`);
            
            const result = await this.socket.sendMessage(jid, { text: message });
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
        
        // Clear auth state from database
        try {
            await this.authState.clearState();
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

