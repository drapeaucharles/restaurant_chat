/**
 * WhatsApp Service using open-wa for Restaurant Chatbot Integration
 * 
 * This service handles:
 * - WhatsApp session management per restaurant
 * - QR code generation for session connection
 * - Incoming message forwarding to FastAPI
 * - Outgoing message sending via WhatsApp
 * - Anti-ban throttling and security features
 */

const { create, Whatsapp } = require('@open-wa/wa-automate');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');

// Configuration
const PORT = process.env.WHATSAPP_PORT || 8002;
const FASTAPI_URL = process.env.FASTAPI_URL || 'http://localhost:8000';
const SESSIONS_DIR = path.join(__dirname, 'sessions');
const QR_DIR = path.join(__dirname, 'qr-codes');
const SHARED_SECRET = process.env.WHATSAPP_SECRET || 'default-secret-change-in-production';
const WHATSAPP_API_KEY = process.env.WHATSAPP_API_KEY || 'supersecretkey123';

// Ensure directories exist
fs.ensureDirSync(SESSIONS_DIR);
fs.ensureDirSync(QR_DIR);

// Express app for API endpoints
const app = express();
app.use(cors());
app.use(express.json());

// Store active WhatsApp clients and QR codes
const activeClients = new Map();
const sessionConfigs = new Map();
const qrCodes = new Map(); // Store QR codes for each session
const sessionStates = new Map(); // Track session connection states

// Utility functions
const delay = ms => new Promise(res => setTimeout(res, ms));

/**
 * Authentication middleware
 */
function authenticateRequest(req, res, next) {
    const authHeader = req.headers.authorization;
    const apiKey = req.headers['x-api-key'];
    const providedSecret = req.body.secret || req.query.secret;
    
    // Check for valid authentication - use WHATSAPP_API_KEY instead of SHARED_SECRET
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
 * Specific authentication middleware for /send endpoint
 */
function authenticateSendRequest(req, res, next) {
    const authHeader = req.headers.authorization;
    
    // Check for Bearer token with WHATSAPP_API_KEY
    if (authHeader === `Bearer ${WHATSAPP_API_KEY}`) {
        next();
    } else {
        console.log(`🔒 Unauthorized send request from ${req.ip} - invalid API key`);
        res.status(403).json({
            success: false,
            error: 'Unauthorized. Invalid API key for message sending.'
        });
    }
}

/**
 * Input validation middleware
 */
function validateSendMessage(req, res, next) {
    const { to, message, session_id } = req.body;
    
    if (!to || typeof to !== 'string' || to.trim().length === 0) {
        return res.status(400).json({
            success: false,
            error: 'Missing or invalid "to" field. Must be a non-empty string.'
        });
    }
    
    if (!message || typeof message !== 'string' || message.trim().length === 0) {
        return res.status(400).json({
            success: false,
            error: 'Missing or invalid "message" field. Must be a non-empty string.'
        });
    }
    
    if (!session_id || typeof session_id !== 'string' || session_id.trim().length === 0) {
        return res.status(400).json({
            success: false,
            error: 'Missing or invalid "session_id" field. Must be a non-empty string.'
        });
    }
    
    // Validate message length (WhatsApp limit is ~4096 characters)
    if (message.length > 4000) {
        return res.status(400).json({
            success: false,
            error: 'Message too long. Maximum length is 4000 characters.'
        });
    }
    
    // Validate phone number format
    const phoneRegex = /^[\+]?[1-9][\d]{0,15}$/;
    const cleanPhone = to.replace(/[^\d+]/g, '');
    if (!phoneRegex.test(cleanPhone)) {
        return res.status(400).json({
            success: false,
            error: 'Invalid phone number format. Use international format (e.g., +1234567890).'
        });
    }
    
    next();
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
 * Create a new WhatsApp session for a restaurant
 */
async function createWhatsAppSession(restaurantId) {
    logWithTimestamp('info', restaurantId, '🔄 Creating WhatsApp session...');
    
    const sessionId = `restaurant_${restaurantId}`;
    const sessionPath = path.join(SESSIONS_DIR, `${restaurantId}.json`);
    const qrPath = path.join(QR_DIR, `${restaurantId}.png`);
    
    try {
        // Configuration for this session
        const config = {
            sessionId: sessionId,
            multiDevice: true,
            authTimeout: 60,
            blockCrashLogs: true,
            disableSpins: true,
            headless: true,
            hostNotificationLang: 'PT_BR',
            logConsole: false,
            popup: false,
            qrTimeout: 30,
            restartOnCrash: true,
            sessionData: sessionPath,
            throwErrorOnTosBlock: false,
            useChrome: true,
            killProcessOnBrowserClose: true,
            safeMode: false,
            qrRefreshS: 15, // Refresh QR every 15 seconds
            onLoadingScreen: (percent, message) => {
                logWithTimestamp('info', restaurantId, `Loading: ${percent}% - ${message}`);
            },
            onQR: (qrData) => {
                logWithTimestamp('info', restaurantId, '📱 QR Code generated');
                // Store QR code data
                qrCodes.set(restaurantId, {
                    data: qrData,
                    timestamp: new Date().toISOString(),
                    path: qrPath
                });
                
                // Save QR code as image file
                try {
                    const qrImage = qrData.replace('data:image/png;base64,', '');
                    fs.writeFileSync(qrPath, qrImage, 'base64');
                    logWithTimestamp('info', restaurantId, `📁 QR code saved to: ${qrPath}`);
                } catch (error) {
                    logWithTimestamp('error', restaurantId, `❌ Failed to save QR code: ${error.message}`);
                }
            }
        };
        
        // Store session config
        sessionConfigs.set(restaurantId, config);
        sessionStates.set(restaurantId, 'creating');
        
        // Create WhatsApp client
        const client = await create(config);
        
        // Store active client
        activeClients.set(restaurantId, client);
        sessionStates.set(restaurantId, 'connected');
        
        logWithTimestamp('success', restaurantId, '✅ WhatsApp session created successfully');
        
        // Set up message handler
        await setupMessageHandler(client, restaurantId);
        
        // Set up connection state handlers
        setupConnectionHandlers(client, restaurantId);
        
        return {
            success: true,
            sessionId: sessionId,
            message: 'Session created successfully'
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Failed to create session: ${error.message}`);
        sessionStates.set(restaurantId, 'error');
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Setup connection state handlers
 */
function setupConnectionHandlers(client, restaurantId) {
    client.onStateChanged((state) => {
        logWithTimestamp('info', restaurantId, `🔄 Connection state changed: ${state}`);
        sessionStates.set(restaurantId, state);
        
        if (state === 'DISCONNECTED' || state === 'UNPAIRED') {
            logWithTimestamp('warning', restaurantId, '⚠️ Session disconnected, cleaning up...');
            cleanupSession(restaurantId);
        }
    });
    
    client.onAnyMessage((message) => {
        logWithTimestamp('debug', restaurantId, `📨 Message activity: ${message.type} from ${message.from}`);
    });
}

/**
 * Cleanup session data
 */
function cleanupSession(restaurantId) {
    try {
        activeClients.delete(restaurantId);
        sessionConfigs.delete(restaurantId);
        qrCodes.delete(restaurantId);
        sessionStates.set(restaurantId, 'disconnected');
        
        // Clean up QR code file
        const qrPath = path.join(QR_DIR, `${restaurantId}.png`);
        if (fs.existsSync(qrPath)) {
            fs.unlinkSync(qrPath);
        }
        
        logWithTimestamp('info', restaurantId, '🧹 Session cleanup completed');
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Error during cleanup: ${error.message}`);
    }
}

/**
 * Setup message handler for incoming WhatsApp messages
 */
async function setupMessageHandler(client, restaurantId) {
    logWithTimestamp('info', restaurantId, '📱 Setting up message handler...');
    
    client.onMessage(async (message) => {
        try {
            logWithTimestamp('info', restaurantId, `📨 Incoming message from ${message.from}: ${message.body?.substring(0, 50)}...`);
            
            // Only process text messages for now
            if (message.type !== 'chat') {
                logWithTimestamp('debug', restaurantId, `⏭️ Skipping non-text message type: ${message.type}`);
                return;
            }
            
            // Prepare payload for FastAPI
            const payload = {
                from_number: message.from,
                message: message.body,
                session_id: `restaurant_${restaurantId}`,
                message_id: message.id,
                timestamp: new Date(message.timestamp * 1000).toISOString(),
                chat_id: message.chatId
            };
            
            // Forward to FastAPI with retry logic
            let retries = 3;
            while (retries > 0) {
                try {
                    const response = await axios.post(`${FASTAPI_URL}/whatsapp/incoming`, payload, {
                        timeout: 10000,
                        headers: {
                            'Content-Type': 'application/json',
                            'X-API-Key': SHARED_SECRET
                        }
                    });
                    
                    logWithTimestamp('success', restaurantId, '✅ Message forwarded to FastAPI successfully');
                    break;
                    
                } catch (apiError) {
                    retries--;
                    logWithTimestamp('error', restaurantId, `❌ Failed to forward message (${3-retries}/3): ${apiError.message}`);
                    
                    if (retries > 0) {
                        await delay(2000); // Wait 2 seconds before retry
                    }
                }
            }
            
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error handling message: ${error.message}`);
        }
    });
    
    logWithTimestamp('success', restaurantId, '✅ Message handler setup complete');
}

/**
 * Send a message via WhatsApp with anti-ban throttling
 */
async function sendWhatsAppMessage(restaurantId, toNumber, message) {
    logWithTimestamp('info', restaurantId, `📤 Preparing to send message to ${toNumber}: ${message.substring(0, 50)}...`);
    
    const client = activeClients.get(restaurantId);
    
    if (!client) {
        throw new Error(`No active WhatsApp session for restaurant: ${restaurantId}`);
    }
    
    try {
        // Anti-ban throttling: Random delay between 2-10 seconds
        const delayMs = Math.floor(2000 + Math.random() * 8000);
        logWithTimestamp('info', restaurantId, `⏱️ Applying anti-ban delay: ${delayMs}ms`);
        await delay(delayMs);
        
        // Format phone number for WhatsApp (ensure it has @c.us suffix)
        let chatId = toNumber;
        if (!chatId.includes('@')) {
            // Remove any non-digit characters except +
            const cleanNumber = toNumber.replace(/[^\d+]/g, '');
            chatId = `${cleanNumber}@c.us`;
        }
        
        logWithTimestamp('info', restaurantId, `📱 Sending to chat ID: ${chatId}`);
        
        // Send message
        const result = await client.sendText(chatId, message);
        
        logWithTimestamp('success', restaurantId, `✅ Message sent successfully: ${result.id}`);
        
        return {
            success: true,
            messageId: result.id,
            delayApplied: delayMs
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Failed to send message: ${error.message}`);
        throw error;
    }
}

/**
 * Get session status
 */
async function getSessionStatus(restaurantId) {
    const client = activeClients.get(restaurantId);
    const state = sessionStates.get(restaurantId) || 'not_connected';
    
    if (!client) {
        return {
            status: state,
            connected: false,
            hasQR: qrCodes.has(restaurantId)
        };
    }
    
    try {
        const connectionState = await client.getConnectionState();
        const batteryLevel = await client.getBatteryLevel();
        
        return {
            status: connectionState,
            connected: connectionState === 'CONNECTED',
            battery: batteryLevel,
            sessionId: `restaurant_${restaurantId}`,
            hasQR: qrCodes.has(restaurantId),
            lastActivity: new Date().toISOString()
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Error getting session status: ${error.message}`);
        return {
            status: 'error',
            connected: false,
            error: error.message,
            hasQR: qrCodes.has(restaurantId)
        };
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
        
        // Check if session already exists
        if (activeClients.has(restaurantId)) {
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
        const result = await createWhatsAppSession(restaurantId);
        
        if (result.success) {
            res.json({
                success: true,
                session_id: session_id,
                status: 'created',
                message: 'Session created successfully. Please scan QR code to connect.',
                qr_available: qrCodes.has(restaurantId)
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
 * Get QR code for a session
 * GET /qr/:sessionId
 */
app.get('/qr/:sessionId', authenticateRequest, async (req, res) => {
    try {
        const { sessionId } = req.params;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, '📱 QR code request received');
        
        const qrData = qrCodes.get(restaurantId);
        
        if (!qrData) {
            return res.status(404).json({
                success: false,
                error: 'QR code not available. Session may not be created or already connected.'
            });
        }
        
        // Check if QR is still valid (not older than 5 minutes)
        const qrAge = Date.now() - new Date(qrData.timestamp).getTime();
        if (qrAge > 5 * 60 * 1000) {
            return res.status(410).json({
                success: false,
                error: 'QR code expired. Please create a new session.'
            });
        }
        
        res.json({
            success: true,
            qr_code: qrData.data,
            timestamp: qrData.timestamp,
            expires_in: Math.max(0, 300 - Math.floor(qrAge / 1000)) // seconds until expiry
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
 * Get QR code image file for frontend (simple PNG endpoint)
 * GET /qr/:sessionId/image
 */
app.get('/qr/:sessionId/image', (req, res) => {
    try {
        const { sessionId } = req.params;
        const restaurantId = sessionId.replace('restaurant_', '');
        const qrPath = path.join(QR_DIR, `${restaurantId}.png`);
        
        logWithTimestamp('info', restaurantId, '📱 QR image request received');
        
        if (fs.existsSync(qrPath)) {
            // Check file age (not older than 5 minutes)
            const stats = fs.statSync(qrPath);
            const fileAge = Date.now() - stats.mtime.getTime();
            
            if (fileAge > 5 * 60 * 1000) {
                logWithTimestamp('warning', restaurantId, '⚠️ QR image expired');
                return res.status(410).send("QR code expired");
            }
            
            logWithTimestamp('success', restaurantId, '✅ Serving QR image file');
            res.sendFile(qrPath);
        } else {
            logWithTimestamp('warning', restaurantId, '⚠️ QR image not found');
            res.status(404).send("QR not found");
        }
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error serving QR image: ${error.message}`);
        res.status(500).send("Internal server error");
    }
});

/**
 * Send a message via WhatsApp
 * POST /message/send
 */
app.post('/message/send', authenticateSendRequest, validateSendMessage, async (req, res) => {
    try {
        const { to, message, session_id } = req.body;
        
        // Extract restaurant ID from session_id
        const restaurantId = session_id.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, `📤 Send request: ${to} - ${message.substring(0, 50)}...`);
        
        const result = await sendWhatsAppMessage(restaurantId, to, message);
        
        res.json({
            success: true,
            message_id: result.messageId,
            delay_applied: result.delayApplied
        });
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error sending message: ${error.message}`);
        res.json({
            success: false,
            error: error.message
        });
    }
});

/**
 * Get session status
 * GET /session/:sessionId/status
 */
app.get('/session/:sessionId/status', authenticateRequest, async (req, res) => {
    try {
        const { sessionId } = req.params;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        const status = await getSessionStatus(restaurantId);
        
        res.json(status);
        
    } catch (error) {
        logWithTimestamp('error', null, `❌ Error getting session status: ${error.message}`);
        res.status(500).json({
            status: 'error',
            error: error.message
        });
    }
});

/**
 * Delete/disconnect a session
 * DELETE /session/:sessionId
 */
app.delete('/session/:sessionId', authenticateRequest, async (req, res) => {
    try {
        const { sessionId } = req.params;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, '🗑️ Session deletion request received');
        
        const client = activeClients.get(restaurantId);
        
        if (client) {
            try {
                await client.kill();
                logWithTimestamp('info', restaurantId, '✅ WhatsApp client terminated');
            } catch (error) {
                logWithTimestamp('warning', restaurantId, `⚠️ Error terminating client: ${error.message}`);
            }
        }
        
        cleanupSession(restaurantId);
        
        res.json({
            success: true,
            message: 'Session deleted successfully'
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
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        service: 'whatsapp-service',
        activeSessions: activeClients.size,
        timestamp: new Date().toISOString(),
        version: '2.0.0'
    });
});

/**
 * List active sessions
 */
app.get('/sessions', authenticateRequest, (req, res) => {
    const sessions = Array.from(activeClients.keys()).map(restaurantId => ({
        restaurantId,
        sessionId: `restaurant_${restaurantId}`,
        active: true,
        state: sessionStates.get(restaurantId) || 'unknown',
        hasQR: qrCodes.has(restaurantId)
    }));
    
    res.json({
        sessions,
        count: sessions.length,
        timestamp: new Date().toISOString()
    });
});

// Start the Express server
app.listen(PORT, () => {
    console.log(`🚀 WhatsApp Service v2.0 running on port ${PORT}`);
    console.log(`📡 FastAPI URL: ${FASTAPI_URL}`);
    console.log(`📁 Sessions directory: ${SESSIONS_DIR}`);
	console.log("CHROME_PATH:", process.env.CHROME_PATH);
    console.log(`📱 QR codes directory: ${QR_DIR}`);
    console.log(`🔐 Authentication: ${SHARED_SECRET === 'default-secret-change-in-production' ? '⚠️ DEFAULT SECRET' : '✅ CONFIGURED'}`);
    console.log(`🔗 Health check: http://localhost:${PORT}/health`);
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('🛑 Shutting down WhatsApp service...');
    
    // Close all active WhatsApp clients
    for (const [restaurantId, client] of activeClients) {
        try {
            logWithTimestamp('info', restaurantId, '🔌 Closing session...');
            await client.kill();
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error closing session: ${error.message}`);
        }
    }
    
    console.log('✅ WhatsApp service shutdown complete');
    process.exit(0);
});

// Handle uncaught exceptions
process.on('uncaughtException', (error) => {
    console.error('❌ Uncaught Exception:', error);
});

process.on('unhandledRejection', (reason, promise) => {
    console.error('❌ Unhandled Rejection at:', promise, 'reason:', reason);
});

