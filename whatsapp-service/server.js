/**
 * WhatsApp Service using whatsapp-web.js for Restaurant Chatbot Integration
 * 
 * This service handles:
 * - WhatsApp session management per restaurant
 * - QR code generation for session connection
 * - Incoming message forwarding to FastAPI
 * - Outgoing message sending via WhatsApp
 * - Railway-compatible deployment without heavy browser dependencies
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
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
 * Create a new WhatsApp session for a restaurant using whatsapp-web.js
 */
async function createWhatsAppSession(restaurantId) {
    logWithTimestamp('info', restaurantId, '🔄 Creating WhatsApp session with whatsapp-web.js...');
    
    const sessionId = `restaurant_${restaurantId}`;
    const sessionPath = path.join(SESSIONS_DIR, restaurantId);
    const qrPath = path.join(QR_DIR, `${restaurantId}.png`);
    
    try {
        // Check if client already exists
        if (activeClients.has(restaurantId)) {
            const existingClient = activeClients.get(restaurantId);
            const state = await existingClient.getState();
            
            if (state === 'CONNECTED') {
                logWithTimestamp('info', restaurantId, '✅ Session already connected');
                return {
                    success: true,
                    sessionId: sessionId,
                    message: 'Session already connected'
                };
            } else {
                // Clean up existing client
                await existingClient.destroy();
                activeClients.delete(restaurantId);
            }
        }
        
        // Create new WhatsApp client with Railway-compatible settings
        const client = new Client({
            authStrategy: new LocalAuth({
                clientId: restaurantId,
                dataPath: sessionPath
            }),
            puppeteer: {
                headless: true,
                args: [
                    '--no-sandbox',
                    '--disable-setuid-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-accelerated-2d-canvas',
                    '--no-first-run',
                    '--no-zygote',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            }
        });
        
        // Store client
        activeClients.set(restaurantId, client);
        sessionStates.set(restaurantId, 'creating');
        
        // Set up QR code handler
        client.on('qr', (qr) => {
            logWithTimestamp('info', restaurantId, '📱 QR Code generated');
            
            // Store QR code data (whatsapp-web.js provides the QR string directly)
            qrCodes.set(restaurantId, {
                data: qr,
                timestamp: new Date().toISOString(),
                path: qrPath
            });
            
            // Display QR in terminal for debugging
            console.log(`\n📱 QR Code for restaurant ${restaurantId}:`);
            qrcode.generate(qr, { small: true });
            
            // Save QR code string to file for API response
            try {
                fs.writeFileSync(qrPath, qr);
                logWithTimestamp('info', restaurantId, `📁 QR code saved to: ${qrPath}`);
            } catch (error) {
                logWithTimestamp('error', restaurantId, `❌ Failed to save QR code: ${error.message}`);
            }
        });
        
        // Set up ready handler
        client.on('ready', () => {
            logWithTimestamp('success', restaurantId, '✅ WhatsApp client is ready!');
            sessionStates.set(restaurantId, 'connected');
        });
        
        // Set up message handler
        client.on('message', async (message) => {
            try {
                logWithTimestamp('info', restaurantId, `📨 Received message from ${message.from}: ${message.body}`);
                
                // Forward message to FastAPI
                await forwardMessageToFastAPI(message, sessionId);
                
            } catch (error) {
                logWithTimestamp('error', restaurantId, `❌ Error handling message: ${error.message}`);
            }
        });
        
        // Set up disconnection handler
        client.on('disconnected', (reason) => {
            logWithTimestamp('warning', restaurantId, `⚠️ Client disconnected: ${reason}`);
            sessionStates.set(restaurantId, 'disconnected');
            cleanupSession(restaurantId);
        });
        
        // Set up authentication failure handler
        client.on('auth_failure', (message) => {
            logWithTimestamp('error', restaurantId, `❌ Authentication failed: ${message}`);
            sessionStates.set(restaurantId, 'auth_failed');
        });
        
        // Initialize the client
        await client.initialize();
        
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
                await activeClients.get(restaurantId).destroy();
            } catch (destroyError) {
                logWithTimestamp('error', restaurantId, `❌ Error destroying client: ${destroyError.message}`);
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
            message_id: message.id._serialized
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
        
        const state = await client.getState();
        if (state !== 'CONNECTED') {
            throw new Error(`WhatsApp client not connected. Current state: ${state}`);
        }
        
        // Format phone number for WhatsApp (ensure it has country code)
        let formattedNumber = toNumber.replace(/[^\d+]/g, '');
        if (!formattedNumber.includes('@')) {
            formattedNumber = formattedNumber + '@c.us';
        }
        
        logWithTimestamp('info', restaurantId, `📤 Sending message to ${formattedNumber}: ${messageText}`);
        
        const sentMessage = await client.sendMessage(formattedNumber, messageText);
        
        logWithTimestamp('success', restaurantId, `✅ Message sent successfully: ${sentMessage.id._serialized}`);
        
        return {
            success: true,
            message_id: sentMessage.id._serialized
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
                message: 'No session found for this restaurant'
            };
        }
        
        const state = await client.getState();
        const info = client.info;
        
        return {
            status: state.toLowerCase(),
            connected: state === 'CONNECTED',
            session_id: `restaurant_${restaurantId}`,
            phone_number: info ? info.wid.user : null,
            platform: info ? info.platform : null,
            last_seen: new Date().toISOString()
        };
        
    } catch (error) {
        logWithTimestamp('error', restaurantId, `❌ Error getting session status: ${error.message}`);
        return {
            status: 'error',
            connected: false,
            message: error.message
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
            await client.destroy();
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
                error: 'QR code not found. Session may not be created or already connected.'
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
 * Health check endpoint
 * GET /health
 */
app.get('/health', (req, res) => {
    res.json({
        status: 'healthy',
        service: 'whatsapp-web.js',
        timestamp: new Date().toISOString(),
        active_sessions: activeClients.size
    });
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down WhatsApp service...');
    
    // Close all active clients
    for (const [restaurantId, client] of activeClients) {
        try {
            await client.destroy();
            logWithTimestamp('info', restaurantId, '✅ Client destroyed');
        } catch (error) {
            logWithTimestamp('error', restaurantId, `❌ Error destroying client: ${error.message}`);
        }
    }
    
    process.exit(0);
});

// Start server
app.listen(PORT, () => {
    console.log(`\n🚀 WhatsApp Service (whatsapp-web.js) running on port ${PORT}`);
    console.log(`📱 Ready to handle WhatsApp sessions for restaurants`);
    console.log(`🔗 FastAPI URL: ${FASTAPI_URL}`);
    console.log(`📁 Sessions directory: ${SESSIONS_DIR}`);
    console.log(`📱 QR codes directory: ${QR_DIR}`);
    console.log(`🔑 Using API key: ${WHATSAPP_API_KEY.substring(0, 10)}...`);
});

