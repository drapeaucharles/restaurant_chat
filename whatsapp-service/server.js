/**
 * WhatsApp Service using Baileys for Restaurant Chatbot Integration
 * 
 * This service handles:
 * - WhatsApp session management per restaurant using Baileys (100% BROWSER-FREE!)
 * - Session auth state persistence for Railway deployment resilience
 * - QR code generation for initial session connection
 * - Incoming message forwarding to FastAPI
 * - Outgoing message sending via WhatsApp
 * - 100% browser-free deployment compatible with Railway/serverless
 */

const { makeWASocket, DisconnectReason, useMultiFileAuthState } = require('@whiskeysockets/baileys');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');
const QRCode = require('qrcode');

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

// Store active WhatsApp sockets and QR codes
const activeSockets = new Map();
const qrCodes = new Map(); // Store QR codes for each session
const sessionStates = new Map(); // Track session connection states
const connectionPromises = new Map(); // Track connection promises

/**
 * Authentication middleware
 */
function authenticateRequest(req, res, next) {
    const authHeader = req.headers.authorization;
    const apiKey = req.headers['x-api-key'];
    const providedSecret = req.body.secret || req.query.secret;
    
    // Check for valid authentication
    if (authHeader === `Bearer ${WHATSAPP_API_KEY}` || 
        apiKey === WHATSAPP_API_KEY || 
        providedSecret === WHATSAPP_API_KEY ||
        authHeader === `Bearer ${SHARED_SECRET}` || 
        apiKey === SHARED_SECRET || 
        providedSecret === SHARED_SECRET) {
        next();
    } else {
        console.log(`🔒 Unauthorized request from ${req.ip} to ${req.path}`);
        res.status(401).json({
            success: false,
            error: 'Unauthorized. Please provide valid authentication.'
        });
    }
}

/**
 * Enhanced logging function
 */
function logWithTimestamp(level, restaurantId, message, data = null) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}] [Restaurant: ${restaurantId || 'N/A'}]`;
    
    if (data) {
        console.log(`${prefix} ${message}`, data);
    } else {
        console.log(`${prefix} ${message}`);
    }
}

/**
 * Get session auth directory for a restaurant
 */
function getSessionDir(restaurantId) {
    return path.join(SESSIONS_DIR, restaurantId, 'auth_info_baileys');
}

/**
 * Check if session auth state exists for a restaurant
 */
function hasSessionAuth(restaurantId) {
    const sessionDir = getSessionDir(restaurantId);
    return fs.existsSync(sessionDir) && fs.readdirSync(sessionDir).length > 0;
}

/**
 * Create a new WhatsApp session for a restaurant using Baileys
 */
async function createBaileysSession(restaurantId) {
    logWithTimestamp('info', restaurantId, '🔄 Creating WhatsApp session with Baileys...');
    
    const sessionName = `restaurant_${restaurantId}`;
    const sessionDir = getSessionDir(restaurantId);
    
    try {
        // Check if socket already exists and is connected
        if (activeSockets.has(restaurantId)) {
            const existingSocket = activeSockets.get(restaurantId);
            try {
                if (existingSocket.user) {
                    logWithTimestamp('info', restaurantId, '✅ Session already connected');
                    return {
                        success: true,
                        sessionId: sessionName,
                        message: 'Session already connected'
                    };
                }
            } catch (error) {
                logWithTimestamp('warning', restaurantId, '⚠️ Existing socket check failed, creating new session');
            }
            
            // Clean up existing socket
            try {
                existingSocket.end();
            } catch (error) {
                logWithTimestamp('warning', restaurantId, `⚠️ Error closing existing socket: ${error.message}`);
            }
            activeSockets.delete(restaurantId);
        }
        
        // Check if there's already a connection in progress
        if (connectionPromises.has(restaurantId)) {
            logWithTimestamp('info', restaurantId, '⏳ Connection already in progress, waiting...');
            return await connectionPromises.get(restaurantId);
        }
        
        logWithTimestamp('info', restaurantId, `📁 Session directory: ${sessionDir}`);
        logWithTimestamp('info', restaurantId, `🔑 Has existing auth: ${hasSessionAuth(restaurantId)}`);
        
        // Create connection promise
        const connectionPromise = createSocketConnection(restaurantId, sessionDir, sessionName);
        connectionPromises.set(restaurantId, connectionPromise);
        
        try {
            const result = await connectionPromise;
            return result;
        } finally {
            connectionPromises.delete(restaurantId);
        }
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Failed to create session: ${error.message}`);
        sessionStates.set(restaurantId, 'error');
        
        // Clean up on error
        if (activeSockets.has(restaurantId)) {
            try {
                activeSockets.get(restaurantId).end();
            } catch (closeError) {
                logWithTimestamp('error', restaurantId, `❌ Error closing socket: ${closeError.message}`);
            }
            activeSockets.delete(restaurantId);
        }
        
        connectionPromises.delete(restaurantId);
        
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Create socket connection with improved error handling
 */
async function createSocketConnection(restaurantId, sessionDir, sessionName) {
    return new Promise(async (resolve, reject) => {
        let connectionTimeout;
        let qrTimeout;
        let isResolved = false;
        
        const resolveOnce = (result) => {
            if (!isResolved) {
                isResolved = true;
                if (connectionTimeout) clearTimeout(connectionTimeout);
                if (qrTimeout) clearTimeout(qrTimeout);
                resolve(result);
            }
        };
        
        const rejectOnce = (error) => {
            if (!isResolved) {
                isResolved = true;
                if (connectionTimeout) clearTimeout(connectionTimeout);
                if (qrTimeout) clearTimeout(qrTimeout);
                reject(error);
            }
        };
        
        try {
            // Ensure session directory exists
            fs.ensureDirSync(sessionDir);
            
            // Create auth state
            const { state, saveCreds } = await useMultiFileAuthState(sessionDir);
            
            // Set connection timeout
            connectionTimeout = setTimeout(() => {
                rejectOnce(new Error('Connection timeout after 30 seconds'));
            }, 30000);
            
            // Create new WhatsApp socket with Baileys
            const sock = makeWASocket({
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
                    return { conversation: '' };
                }
            });
            
            // Store socket immediately
            activeSockets.set(restaurantId, sock);
            sessionStates.set(restaurantId, 'creating');
            
            // Handle connection updates (including QR code)
            sock.ev.on('connection.update', async (update) => {
                try {
                    await handleConnectionUpdate(update, restaurantId, sessionName, resolveOnce, rejectOnce);
                } catch (error) {
                    logWithTimestamp('error', restaurantId, `❌ Error in connection update: ${error.message}`);
                    rejectOnce(error);
                }
            });
            
            // Handle credential updates
            sock.ev.on('creds.update', saveCreds);
            
            // Handle incoming messages
            sock.ev.on('messages.upsert', async (messageUpdate) => {
                await handleMessages(messageUpdate, restaurantId, sessionName);
            });
            
            // Handle socket errors
            sock.ev.on('connection.error', (error) => {
                logWithTimestamp('error', restaurantId, `❌ Socket error: ${error.message}`);
                rejectOnce(error);
            });
            
            logWithTimestamp('success', restaurantId, '✅ Baileys socket initialized, waiting for connection...');
            
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error creating socket: ${error.message}`);
            rejectOnce(error);
        }
    });
}

/**
 * Handle connection updates from Baileys with improved QR handling
 */
async function handleConnectionUpdate(update, restaurantId, sessionName, resolveOnce, rejectOnce) {
    const { connection, lastDisconnect, qr } = update;
    
    logWithTimestamp('info', restaurantId, `🔄 Connection update: ${connection || 'undefined'}`);
    
    if (qr) {
        logWithTimestamp('info', restaurantId, '📱 QR Code generated');
        
        try {
            // Generate base64 QR code image
            const qrImage = await QRCode.toDataURL(qr);
            
            // Store QR code data
            qrCodes.set(restaurantId, {
                data: qrImage,
                raw: qr,
                timestamp: new Date().toISOString()
            });
            
            sessionStates.set(restaurantId, 'qr_ready');
            
            // Display QR in terminal for debugging
            console.log(`\n📱 QR Code for restaurant ${restaurantId}:`);
            console.log(await QRCode.toString(qr, { type: 'terminal', small: true }));
            console.log(`🔗 QR Raw: ${qr}\n`);
            
            logWithTimestamp('info', restaurantId, '📁 QR code stored in memory for API access');
            
            // Resolve with QR ready status
            resolveOnce({
                success: true,
                sessionId: sessionName,
                message: 'Session created successfully. QR code ready for scanning.',
                qr_ready: true
            });
            
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error generating QR code: ${error.message}`);
            rejectOnce(new Error(`QR generation failed: ${error.message}`));
        }
    }
    
    if (connection === 'close') {
        const shouldReconnect = lastDisconnect?.error?.output?.statusCode !== DisconnectReason.loggedOut;
        const errorMessage = lastDisconnect?.error?.message || 'Unknown error';
        
        logWithTimestamp('warning', restaurantId, `⚠️ Connection closed: ${errorMessage}`);
        
        if (shouldReconnect) {
            logWithTimestamp('info', restaurantId, '🔄 Will attempt to reconnect...');
            sessionStates.set(restaurantId, 'reconnecting');
            
            // Don't reject here if QR was already generated
            if (!qrCodes.has(restaurantId)) {
                rejectOnce(new Error(`Connection closed before QR generation: ${errorMessage}`));
            }
        } else {
            logWithTimestamp('warning', restaurantId, '🚪 Logged out, cleaning up session');
            sessionStates.set(restaurantId, 'logged_out');
            activeSockets.delete(restaurantId);
            qrCodes.delete(restaurantId);
            
            if (!qrCodes.has(restaurantId)) {
                rejectOnce(new Error('Session logged out'));
            }
        }
    } else if (connection === 'open') {
        logWithTimestamp('success', restaurantId, '✅ WhatsApp connection opened successfully!');
        sessionStates.set(restaurantId, 'connected');
        
        // Clear QR code once connected
        qrCodes.delete(restaurantId);
        
        // Get socket info
        const sock = activeSockets.get(restaurantId);
        if (sock && sock.user) {
            logWithTimestamp('info', restaurantId, `📱 Connected as: ${sock.user.id}`);
        }
        
        // If not already resolved with QR, resolve with connected status
        resolveOnce({
            success: true,
            sessionId: sessionName,
            message: 'Session connected successfully',
            connected: true
        });
        
    } else if (connection === 'connecting') {
        logWithTimestamp('info', restaurantId, '🔄 Connecting to WhatsApp...');
        sessionStates.set(restaurantId, 'connecting');
    }
}

/**
 * Handle incoming messages from Baileys
 */
async function handleMessages(messageUpdate, restaurantId, sessionName) {
    const { messages, type } = messageUpdate;
    
    if (type !== 'notify') return; // Only process new messages
    
    for (const message of messages) {
        try {
            // Skip messages from self
            if (message.key.fromMe) continue;
            
            // Extract message content
            const messageContent = message.message?.conversation || 
                                 message.message?.extendedTextMessage?.text || 
                                 '';
            
            if (!messageContent) continue;
            
            logWithTimestamp('info', restaurantId, `📨 Received message from ${message.key.remoteJid}: ${messageContent}`);
            
            // Forward message to FastAPI
            await forwardMessageToFastAPI(message, sessionName);
            
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error handling message: ${error.message}`);
        }
    }
}

/**
 * Forward incoming WhatsApp message to FastAPI
 */
async function forwardMessageToFastAPI(message, sessionId) {
    try {
        const messageContent = message.message?.conversation || 
                             message.message?.extendedTextMessage?.text || 
                             '';
        
        const payload = {
            from_number: message.key.remoteJid,
            message: messageContent,
            session_id: sessionId,
            timestamp: new Date(message.messageTimestamp * 1000).toISOString(),
            message_id: message.key.id,
            message_type: 'chat',
            is_group: message.key.remoteJid.includes('@g.us'),
            sender: message.key.participant || message.key.remoteJid
        };
        
        logWithTimestamp('info', sessionId, `📤 Forwarding message to FastAPI: ${FASTAPI_URL}/whatsapp/incoming`);
        
        const response = await axios.post(`${FASTAPI_URL}/whatsapp/incoming`, payload, {
            headers: {
                'Content-Type': 'application/json'
            },
            timeout: 10000
        });
        
        logWithTimestamp('success', sessionId, `✅ Message forwarded successfully: ${response.status}`);
        
    } catch (error) {
        logWithTimestamp('error', sessionId, `❌ Failed to forward message to FastAPI: ${error.message}`);
    }
}

/**
 * Send a message via WhatsApp using Baileys
 */
async function sendBaileysMessage(restaurantId, toNumber, messageText) {
    try {
        const sock = activeSockets.get(restaurantId);
        
        if (!sock) {
            throw new Error('No active WhatsApp socket for this restaurant');
        }
        
        if (!sock.user) {
            throw new Error('WhatsApp socket not connected');
        }
        
        // Format phone number for WhatsApp (ensure it has country code and @s.whatsapp.net)
        let formattedNumber = toNumber.replace(/[^\d+]/g, '');
        if (!formattedNumber.includes('@')) {
            formattedNumber = formattedNumber + '@s.whatsapp.net';
        }
        
        logWithTimestamp('info', restaurantId, `📤 Sending message to ${formattedNumber}: ${messageText}`);
        
        const result = await sock.sendMessage(formattedNumber, { text: messageText });
        
        logWithTimestamp('success', restaurantId, `✅ Message sent successfully: ${result.key.id}`);
        
        return {
            success: true,
            message_id: result.key.id
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Failed to send message: ${error.message}`);
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Get session status
 */
async function getSessionStatus(restaurantId) {
    try {
        const sock = activeSockets.get(restaurantId);
        
        if (!sock) {
            return {
                status: 'not_found',
                connected: false,
                message: 'No session found for this restaurant',
                has_auth: hasSessionAuth(restaurantId),
                qr_available: qrCodes.has(restaurantId)
            };
        }
        
        const isConnected = !!sock.user;
        const currentState = sessionStates.get(restaurantId) || 'unknown';
        
        let phoneNumber = null;
        let deviceInfo = null;
        try {
            if (isConnected && sock.user) {
                phoneNumber = sock.user.id.split(':')[0];
                deviceInfo = {
                    platform: 'WhatsApp',
                    id: sock.user.id,
                    name: sock.user.name || 'Unknown'
                };
            }
        } catch (error) {
            logWithTimestamp('warning', restaurantId, `⚠️ Could not get device info: ${error.message}`);
        }
        
        return {
            status: currentState,
            connected: isConnected,
            session_id: `restaurant_${restaurantId}`,
            phone_number: phoneNumber,
            device_info: deviceInfo,
            has_auth: hasSessionAuth(restaurantId),
            qr_available: qrCodes.has(restaurantId),
            last_seen: new Date().toISOString()
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Error getting session status: ${error.message}`);
        return {
            status: 'error',
            connected: false,
            message: error.message,
            has_auth: hasSessionAuth(restaurantId),
            qr_available: false
        };
    }
}

/**
 * Clean up session
 */
async function cleanupSession(restaurantId) {
    try {
        logWithTimestamp('info', restaurantId, '🧹 Cleaning up session...');
        
        if (activeSockets.has(restaurantId)) {
            const sock = activeSockets.get(restaurantId);
            try {
                sock.end();
            } catch (error) {
                logWithTimestamp('warning', restaurantId, `⚠️ Error closing socket: ${error.message}`);
            }
            activeSockets.delete(restaurantId);
        }
        
        sessionStates.delete(restaurantId);
        qrCodes.delete(restaurantId);
        connectionPromises.delete(restaurantId);
        
        logWithTimestamp('success', restaurantId, '✅ Session cleaned up successfully');
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Error cleaning up session: ${error.message}`);
    }
}

// API Routes

/**
 * Create a new WhatsApp session
 * POST /session/create
 */
app.post('/session/create', authenticateRequest, async (req, res) => {
    try {
        const { session_id, webhook_url } = req.body;
        
        if (!session_id) {
            return res.status(400).json({
                success: false,
                error: 'session_id is required'
            });
        }
        
        // Extract restaurant ID from session_id (format: restaurant_123)
        const restaurantId = session_id.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, '🔄 Session creation request received');
        
        // Check if session already exists and is connected
        if (activeSockets.has(restaurantId)) {
            const status = await getSessionStatus(restaurantId);
            
            if (status.connected) {
                return res.json({
                    success: true,
                    session_id: session_id,
                    status: 'already_connected',
                    message: 'Session already exists and is connected'
                });
            }
        }
        
        // Create new session
        const result = await createBaileysSession(restaurantId);
        
        if (result.success) {
            res.json({
                success: true,
                session_id: session_id,
                status: result.qr_ready ? 'qr_ready' : (result.connected ? 'connected' : 'created'),
                message: result.message,
                qr_available: qrCodes.has(restaurantId),
                has_auth: hasSessionAuth(restaurantId)
            });
        } else {
            res.status(500).json({
                success: false,
                error: result.error
            });
        }
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error creating session: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Send a message via WhatsApp
 * POST /message/send
 */
app.post('/message/send', authenticateRequest, async (req, res) => {
    try {
        const { to, message, session_id } = req.body;
        
        if (!to || !message || !session_id) {
            return res.status(400).json({
                success: false,
                error: 'to, message, and session_id are required'
            });
        }
        
        // Extract restaurant ID from session_id
        const restaurantId = session_id.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, `📤 Send message request: ${to} - ${message}`);
        
        const result = await sendBaileysMessage(restaurantId, to, message);
        
        res.json(result);
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error sending message: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Get session status
 * GET /session/:sessionId/status
 */
app.get('/session/:sessionId/status', async (req, res) => {
    try {
        const sessionId = req.params.sessionId;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, '📊 Status check request');
        
        const status = await getSessionStatus(restaurantId);
        
        res.json(status);
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error getting status: ${error.message}`);
        res.status(500).json({
            status: 'error',
            connected: false,
            message: error.message
        });
    }
});

/**
 * Get QR code for session
 * GET /session/:sessionId/qr
 */
app.get('/session/:sessionId/qr', async (req, res) => {
    try {
        const sessionId = req.params.sessionId;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        const qrData = qrCodes.get(restaurantId);
        
        if (!qrData) {
            return res.status(404).json({
                success: false,
                error: 'QR code not found. Session may not be created or already connected.',
                has_auth: hasSessionAuth(restaurantId)
            });
        }
        
        res.json({
            success: true,
            qr_code: qrData.data,
            qr_raw: qrData.raw,
            timestamp: qrData.timestamp
        });
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error getting QR code: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Delete session and auth state
 * DELETE /session/:sessionId
 */
app.delete('/session/:sessionId', authenticateRequest, async (req, res) => {
    try {
        const sessionId = req.params.sessionId;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, '🗑️ Session deletion request');
        
        // Clean up active session
        await cleanupSession(restaurantId);
        
        // Delete session auth directory
        const sessionDir = getSessionDir(restaurantId);
        if (fs.existsSync(sessionDir)) {
            fs.removeSync(sessionDir);
            logWithTimestamp('info', restaurantId, '🗑️ Session auth directory deleted');
        }
        
        res.json({
            success: true,
            message: 'Session and auth state deleted successfully'
        });
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error deleting session: ${error.message}`);
        res.status(500).json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Health check endpoint
 * GET /health
 */
app.get('/health', (req, res) => {
    const sessionDirs = fs.readdirSync(SESSIONS_DIR).filter(f => 
        fs.statSync(path.join(SESSIONS_DIR, f)).isDirectory()
    );
    
    res.json({
        status: 'healthy',
        service: 'Baileys WhatsApp Service',
        version: '6.7.x',
        browser_free: true,
        websocket_only: true,
        timestamp: new Date().toISOString(),
        active_sessions: activeSockets.size,
        sessions_with_auth: sessionDirs.length,
        session_directories: sessionDirs,
        node_version: process.version
    });
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down Baileys WhatsApp service...');
    
    // Close all active sockets
    for (const [restaurantId, sock] of activeSockets) {
        try {
            sock.end();
            logWithTimestamp('info', restaurantId, '✅ Socket closed');
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error closing socket: ${error.message}`);
        }
    }
    
    process.exit(0);
});

// Start server
app.listen(PORT, '0.0.0.0', () => {
    console.log(`\n🚀 Baileys WhatsApp Service running on port ${PORT}`);
    console.log(`📱 100% Browser-free WhatsApp automation ready!`);
    console.log(`🔗 FastAPI URL: ${FASTAPI_URL}`);
    console.log(`📁 Sessions directory: ${SESSIONS_DIR}`);
    console.log(`🔑 Using API key: ${WHATSAPP_API_KEY.substring(0, 10)}...`);
    console.log(`🚫 NO Puppeteer, NO Chromium, NO browser dependencies!`);
    console.log(`⚡ Powered by Baileys WebSocket protocol`);
    console.log(`🌐 Node version: ${process.version}`);
    
    // Log existing session auth directories
    const sessionDirs = fs.readdirSync(SESSIONS_DIR).filter(f => 
        fs.statSync(path.join(SESSIONS_DIR, f)).isDirectory()
    );
    console.log(`💾 Found ${sessionDirs.length} existing session directories`);
    sessionDirs.forEach(dir => {
        console.log(`   - ${dir}`);
    });
});

