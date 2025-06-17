/**
 * WhatsApp Service using @wppconnect-team/wa-js for Restaurant Chatbot Integration
 * 
 * This service handles:
 * - WhatsApp session management per restaurant using WebSocket (no browser!)
 * - Session token persistence for Railway deployment resilience
 * - QR code generation for initial session connection
 * - Incoming message forwarding to FastAPI
 * - Outgoing message sending via WhatsApp
 * - Browser-free deployment compatible with Railway/serverless
 */

const { create, Client } = require('@wppconnect-team/wa-js');
const express = require('express');
const cors = require('cors');
const axios = require('axios');
const fs = require('fs-extra');
const path = require('path');

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

// Store active WhatsApp clients and QR codes
const activeClients = new Map();
const qrCodes = new Map(); // Store QR codes for each session
const sessionStates = new Map(); // Track session connection states

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
 * Get session token file path for a restaurant
 */
function getSessionTokenPath(restaurantId) {
    return path.join(SESSIONS_DIR, `${restaurantId}.json`);
}

/**
 * Check if session token exists for a restaurant
 */
function hasSessionToken(restaurantId) {
    const tokenPath = getSessionTokenPath(restaurantId);
    return fs.existsSync(tokenPath);
}

/**
 * Create a new WhatsApp session for a restaurant using @wppconnect-team/wa-js
 */
async function createWhatsAppSession(restaurantId) {
    logWithTimestamp('info', restaurantId, '🔄 Creating WhatsApp session with @wppconnect-team/wa-js...');
    
    const sessionId = `restaurant_${restaurantId}`;
    const sessionTokenPath = getSessionTokenPath(restaurantId);
    
    try {
        // Check if client already exists and is connected
        if (activeClients.has(restaurantId)) {
            const existingClient = activeClients.get(restaurantId);
            try {
                const isConnected = await existingClient.isConnected();
                if (isConnected) {
                    logWithTimestamp('info', restaurantId, '✅ Session already connected');
                    return {
                        success: true,
                        sessionId: sessionId,
                        message: 'Session already connected'
                    };
                }
            } catch (error) {
                logWithTimestamp('warning', restaurantId, '⚠️ Existing client check failed, creating new session');
            }
            
            // Clean up existing client
            try {
                await existingClient.close();
            } catch (error) {
                logWithTimestamp('warning', restaurantId, `⚠️ Error closing existing client: ${error.message}`);
            }
            activeClients.delete(restaurantId);
        }
        
        logWithTimestamp('info', restaurantId, `📁 Session token path: ${sessionTokenPath}`);
        logWithTimestamp('info', restaurantId, `🔑 Has existing token: ${hasSessionToken(restaurantId)}`);
        
        // Create new WhatsApp client with @wppconnect-team/wa-js
        const client = await create({
            session: sessionId,
            catchQR: (base64Qrimg, asciiQR) => {
                logWithTimestamp('info', restaurantId, '📱 QR Code generated');
                
                // Store QR code data
                qrCodes.set(restaurantId, {
                    data: base64Qrimg,
                    ascii: asciiQR,
                    timestamp: new Date().toISOString()
                });
                
                // Display QR in terminal for debugging
                console.log(`\n📱 QR Code for restaurant ${restaurantId}:`);
                console.log(asciiQR);
                
                logWithTimestamp('info', restaurantId, '📁 QR code stored in memory for API access');
            },
            sessionTokenPath: sessionTokenPath,
            headless: true,
            disableWelcome: true,
            logQR: false, // We handle QR display ourselves
            browserArgs: [
                '--no-sandbox',
                '--disable-setuid-sandbox',
                '--disable-dev-shm-usage',
                '--disable-web-security'
            ]
        });
        
        // Store client
        activeClients.set(restaurantId, client);
        sessionStates.set(restaurantId, 'creating');
        
        // Set up message handler
        client.onMessage(async (message) => {
            try {
                logWithTimestamp('info', restaurantId, `📨 Received message from ${message.from}: ${message.body}`);
                
                // Forward message to FastAPI
                await forwardMessageToFastAPI(message, sessionId);
                
            } catch (error) {
                logWithTimestamp('error', restaurantId, `❌ Error handling message: ${error.message}`);
            }
        });
        
        // Set up state change handler
        client.onStateChange((state) => {
            logWithTimestamp('info', restaurantId, `🔄 State changed: ${state}`);
            sessionStates.set(restaurantId, state);
            
            if (state === 'CONNECTED') {
                logWithTimestamp('success', restaurantId, '✅ WhatsApp client is ready!');
                // Clear QR code once connected
                qrCodes.delete(restaurantId);
            }
        });
        
        // Set up logout handler
        client.onLogout(() => {
            logWithTimestamp('warning', restaurantId, '⚠️ Session logged out');
            sessionStates.set(restaurantId, 'logged_out');
            cleanupSession(restaurantId);
        });
        
        // Set up disconnection handler
        client.onDisconnected((reason) => {
            logWithTimestamp('warning', restaurantId, `⚠️ Client disconnected: ${reason}`);
            sessionStates.set(restaurantId, 'disconnected');
        });
        
        logWithTimestamp('success', restaurantId, '✅ WhatsApp session created successfully');
        
        return {
            success: true,
            sessionId: sessionId,
            message: 'Session created successfully'
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Failed to create session: ${error.message}`);
        sessionStates.set(restaurantId, 'error');
        
        // Clean up on error
        if (activeClients.has(restaurantId)) {
            try {
                await activeClients.get(restaurantId).close();
            } catch (closeError) {
                logWithTimestamp('error', restaurantId, `❌ Error closing client: ${closeError.message}`);
            }
            activeClients.delete(restaurantId);
        }
        
        return {
            success: false,
            error: error.message
        };
    }
}

/**
 * Forward incoming WhatsApp message to FastAPI
 */
async function forwardMessageToFastAPI(message, sessionId) {
    try {
        const payload = {
            from_number: message.from,
            message: message.body,
            session_id: sessionId,
            timestamp: new Date().toISOString(),
            message_id: message.id
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
 * Send a message via WhatsApp
 */
async function sendWhatsAppMessage(restaurantId, toNumber, messageText) {
    try {
        const client = activeClients.get(restaurantId);
        
        if (!client) {
            throw new Error('No active WhatsApp client for this restaurant');
        }
        
        const isConnected = await client.isConnected();
        if (!isConnected) {
            throw new Error('WhatsApp client not connected');
        }
        
        // Format phone number for WhatsApp (ensure it has country code)
        let formattedNumber = toNumber.replace(/[^\d+]/g, '');
        if (!formattedNumber.includes('@')) {
            formattedNumber = formattedNumber + '@c.us';
        }
        
        logWithTimestamp('info', restaurantId, `📤 Sending message to ${formattedNumber}: ${messageText}`);
        
        const result = await client.sendText(formattedNumber, messageText);
        
        logWithTimestamp('success', restaurantId, `✅ Message sent successfully: ${result.id}`);
        
        return {
            success: true,
            message_id: result.id
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
        const client = activeClients.get(restaurantId);
        
        if (!client) {
            return {
                status: 'not_found',
                connected: false,
                message: 'No session found for this restaurant',
                has_token: hasSessionToken(restaurantId)
            };
        }
        
        const isConnected = await client.isConnected();
        const currentState = sessionStates.get(restaurantId) || 'unknown';
        
        let phoneNumber = null;
        try {
            if (isConnected) {
                const hostDevice = await client.getHostDevice();
                phoneNumber = hostDevice.wid.user;
            }
        } catch (error) {
            logWithTimestamp('warning', restaurantId, `⚠️ Could not get phone number: ${error.message}`);
        }
        
        return {
            status: currentState,
            connected: isConnected,
            session_id: `restaurant_${restaurantId}`,
            phone_number: phoneNumber,
            has_token: hasSessionToken(restaurantId),
            last_seen: new Date().toISOString()
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Error getting session status: ${error.message}`);
        return {
            status: 'error',
            connected: false,
            message: error.message,
            has_token: hasSessionToken(restaurantId)
        };
    }
}

/**
 * Clean up session
 */
async function cleanupSession(restaurantId) {
    try {
        logWithTimestamp('info', restaurantId, '🧹 Cleaning up session...');
        
        if (activeClients.has(restaurantId)) {
            const client = activeClients.get(restaurantId);
            try {
                await client.close();
            } catch (error) {
                logWithTimestamp('warning', restaurantId, `⚠️ Error closing client: ${error.message}`);
            }
            activeClients.delete(restaurantId);
        }
        
        sessionStates.delete(restaurantId);
        qrCodes.delete(restaurantId);
        
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
                qr_available: qrCodes.has(restaurantId),
                has_token: hasSessionToken(restaurantId)
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
        
        const result = await sendWhatsAppMessage(restaurantId, to, message);
        
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
                has_token: hasSessionToken(restaurantId)
            });
        }
        
        res.json({
            success: true,
            qr_code: qrData.data,
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
 * Delete session and token
 * DELETE /session/:sessionId
 */
app.delete('/session/:sessionId', authenticateRequest, async (req, res) => {
    try {
        const sessionId = req.params.sessionId;
        const restaurantId = sessionId.replace('restaurant_', '');
        
        logWithTimestamp('info', restaurantId, '🗑️ Session deletion request');
        
        // Clean up active session
        await cleanupSession(restaurantId);
        
        // Delete session token file
        const tokenPath = getSessionTokenPath(restaurantId);
        if (fs.existsSync(tokenPath)) {
            fs.unlinkSync(tokenPath);
            logWithTimestamp('info', restaurantId, '🗑️ Session token file deleted');
        }
        
        res.json({
            success: true,
            message: 'Session and token deleted successfully'
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
    res.json({
        status: 'healthy',
        service: '@wppconnect-team/wa-js',
        timestamp: new Date().toISOString(),
        active_sessions: activeClients.size,
        sessions_with_tokens: fs.readdirSync(SESSIONS_DIR).filter(f => f.endsWith('.json')).length
    });
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down WhatsApp service...');
    
    // Close all active clients
    for (const [restaurantId, client] of activeClients) {
        try {
            await client.close();
            logWithTimestamp('info', restaurantId, '✅ Client closed');
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error closing client: ${error.message}`);
        }
    }
    
    process.exit(0);
});

// Start server
app.listen(PORT, () => {
    console.log(`\n🚀 WhatsApp Service (@wppconnect-team/wa-js) running on port ${PORT}`);
    console.log(`📱 Browser-free WhatsApp automation ready!`);
    console.log(`🔗 FastAPI URL: ${FASTAPI_URL}`);
    console.log(`📁 Sessions directory: ${SESSIONS_DIR}`);
    console.log(`🔑 Using API key: ${WHATSAPP_API_KEY.substring(0, 10)}...`);
    
    // Log existing session tokens
    const tokenFiles = fs.readdirSync(SESSIONS_DIR).filter(f => f.endsWith('.json'));
    console.log(`💾 Found ${tokenFiles.length} existing session tokens`);
    tokenFiles.forEach(file => {
        const restaurantId = file.replace('.json', '');
        console.log(`   - ${restaurantId}`);
    });
});

