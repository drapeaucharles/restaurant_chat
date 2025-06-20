/**
 * WhatsApp Service using Baileys - HYBRID FILE+DATABASE VERSION
 * Uses file-based auth (reliable) with database backup (persistent)
 */

const express = require('express');
const { makeWASocket, DisconnectReason, useMultiFileAuthState, fetchLatestBaileysVersion, downloadMediaMessage } = require('@whiskeysockets/baileys');
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

// Database connection (for backup/restore only)
const pool = new Pool({
    connectionString: process.env.DATABASE_URL || 'postgresql://postgres:password@localhost:5432/railway',
    ssl: process.env.NODE_ENV === 'production' ? { rejectUnauthorized: false } : false
});

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
 * Backup session to database
 */
async function backupSessionToDatabase(sessionId, sessionDir) {
    try {
        const credsPath = path.join(sessionDir, 'creds.json');
        const keysDir = path.join(sessionDir, 'keys');
        
        if (!fs.existsSync(credsPath)) {
            return;
        }
        
        const creds = await fs.readJson(credsPath);
        let keys = {};
        
        if (fs.existsSync(keysDir)) {
            const keyFiles = await fs.readdir(keysDir);
            for (const keyFile of keyFiles) {
                if (keyFile.endsWith('.json')) {
                    const keyData = await fs.readJson(path.join(keysDir, keyFile));
                    keys[keyFile.replace('.json', '')] = keyData;
                }
            }
        }
        
        const client = await pool.connect();
        await client.query(`
            INSERT INTO whatsapp_sessions (session_id, creds, keys, updated_at) 
            VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
            ON CONFLICT (session_id) 
            DO UPDATE SET 
                creds = EXCLUDED.creds,
                keys = EXCLUDED.keys,
                updated_at = CURRENT_TIMESTAMP
        `, [sessionId, JSON.stringify(creds), JSON.stringify(keys)]);
        
        client.release();
        console.log(`💾 [${sessionId}] Session backed up to database`);
        
    } catch (error) {
        console.error(`❌ [${sessionId}] Error backing up session:`, error);
    }
}

/**
 * Restore session from database
 */
async function restoreSessionFromDatabase(sessionId, sessionDir) {
    try {
        const client = await pool.connect();
        const result = await client.query(
            'SELECT creds, keys FROM whatsapp_sessions WHERE session_id = $1',
            [sessionId]
        );
        
        if (result.rows.length > 0) {
            const { creds, keys } = result.rows[0];
            
            // Ensure session directory exists
            await fs.ensureDir(sessionDir);
            await fs.ensureDir(path.join(sessionDir, 'keys'));
            
            // Write creds.json
            await fs.writeJson(path.join(sessionDir, 'creds.json'), creds);
            
            // Write key files
            for (const [keyName, keyData] of Object.entries(keys)) {
                await fs.writeJson(path.join(sessionDir, 'keys', `${keyName}.json`), keyData);
            }
            
            console.log(`📁 [${sessionId}] Session restored from database`);
            client.release();
            return true;
        }
        
        client.release();
        return false;
        
    } catch (error) {
        console.error(`❌ [${sessionId}] Error restoring session:`, error);
        return false;
    }
}

/**
 * Session Management Class - HYBRID FILE+DATABASE VERSION
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
            
            // Try to restore session from database first (Railway startup)
            if (!fs.existsSync(this.sessionDir) || fs.readdirSync(this.sessionDir).length === 0) {
                console.log(`📥 [${this.sessionId}] Attempting to restore session from database...`);
                const restored = await restoreSessionFromDatabase(this.sessionId, this.sessionDir);
                if (restored) {
                    console.log(`✅ [${this.sessionId}] Session restored from database`);
                } else {
                    console.log(`📁 [${this.sessionId}] No session found in database, creating new`);
                }
            }
            
            // Ensure session directory exists
            fs.ensureDirSync(this.sessionDir);
            
            // Load auth state using the WORKING method
            const { state, saveCreds } = await useMultiFileAuthState(this.sessionDir);
            
            console.log(`📁 [${this.sessionId}] Session directory: ${this.sessionDir}`);
            console.log(`🔑 [${this.sessionId}] Auth state loaded, has creds: ${!!state.creds?.noiseKey}`);
            
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

            // Set up event handlers with database backup
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
                        
                        // Backup session to database when connected
                        backupSessionToDatabase(this.sessionId, this.sessionDir);
                        
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
        // Handle credential updates with database backup
        this.socket.ev.on('creds.update', async () => {
            console.log(`💾 [${this.sessionId}] Saving credentials...`);
            await saveCreds();
            console.log(`✅ [${this.sessionId}] Credentials saved successfully`);
            
            // Also backup to database
            setTimeout(() => {
                backupSessionToDatabase(this.sessionId, this.sessionDir);
            }, 1000);
        });

        // Handle incoming messages
        this.socket.ev.on('messages.upsert', async (m) => {
            const message = m.messages[0];
            if (!message.key.fromMe && message.message) {
                await this.forwardMessageToFastAPI(message);
            }
        });
    }

    async forwardMessageToFastAPI(message) {
        try {
            console.log(`🔍 ===== WHATSAPP INCOMING MESSAGE =====`);
            
            // Extract phone number from Baileys message
            const fromNumber = message.key.remoteJid?.replace('@s.whatsapp.net', '') || 'unknown';
            console.log(`📱 From: ${fromNumber}`);
            
            // Check if this is an audio message
            const isAudioMessage = message.message?.audioMessage;
            
            if (isAudioMessage) {
                console.log(`🎤 Audio message detected`);
                await this.handleAudioMessage(message, fromNumber);
                return;
            }
            
            // Extract message text from Baileys message object (existing text logic)
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
            
            console.log(`💬 Text Message: '${messageText}'`);
            console.log(`🔗 Session ID: ${this.sessionId}`);

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
                console.error(`❌ [${this.sessionId}] Failed to forward message to FastAPI: ${response.status}`);
            } else {
                console.log(`✅ [${this.sessionId}] Text message forwarded successfully to FastAPI`);
            }
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error forwarding message:`, error);
        }
    }

    async handleAudioMessage(message, fromNumber) {
        try {
            console.log(`🎤 ===== PROCESSING AUDIO MESSAGE =====`);
            
            const audioMessage = message.message.audioMessage;
            console.log(`📁 Audio details: mimetype=${audioMessage.mimetype}, seconds=${audioMessage.seconds}`);
            
            // Step 1: Download the audio file
            console.log(`📥 Step 1: Downloading audio from WhatsApp...`);
            const audioBuffer = await downloadMediaMessage(message, 'buffer', {}, { reuploadRequest: true }, this.socket);
            console.log(`✅ Downloaded audio buffer: ${audioBuffer.length} bytes`);
            
            if (!audioBuffer || audioBuffer.length === 0) {
                throw new Error('Failed to download audio: empty buffer received');
            }
            
            // Step 2: Determine file extension based on mimetype
            console.log(`🔍 Step 2: Determining file format...`);
            let fileExtension = '.ogg'; // Default for WhatsApp
            if (audioMessage.mimetype?.includes('mp4')) fileExtension = '.m4a';
            else if (audioMessage.mimetype?.includes('mpeg')) fileExtension = '.mp3';
            console.log(`📄 File extension determined: ${fileExtension} (mimetype: ${audioMessage.mimetype})`);
            
            // Step 3: Create FormData for multipart upload
            console.log(`📦 Step 3: Creating FormData for upload...`);
            const FormData = require('form-data');
            const form = new FormData();
            
            // Add audio file
            const filename = `audio_${Date.now()}${fileExtension}`;
            form.append('file', audioBuffer, {
                filename: filename,
                contentType: audioMessage.mimetype || 'audio/ogg'
            });
            
            // Add form fields
            form.append('client_id', fromNumber);
            form.append('restaurant_id', this.sessionId); // Use session_id as restaurant_id
            form.append('table_id', ''); // Empty for WhatsApp messages
            
            console.log(`✅ FormData created with file: ${filename}`);
            console.log(`📋 Form fields: client_id=${fromNumber}, restaurant_id=${this.sessionId}`);
            
            // Step 4: Send to FastAPI
            const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
            console.log(`🚀 Step 4: Sending audio to FastAPI: ${fastApiUrl}/speech-to-text`);
            
            if (!process.env.FASTAPI_URL) {
                console.warn(`⚠️ FASTAPI_URL not set, using default: ${fastApiUrl}`);
            }
            
            console.log(`📡 Making HTTP request to FastAPI...`);
            const response = await fetch(`${fastApiUrl}/speech-to-text`, {
                method: 'POST',
                body: form,
                headers: form.getHeaders()
            });
            
            console.log(`📨 Response received: ${response.status} ${response.statusText}`);
            
            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ [${this.sessionId}] Speech-to-text failed: ${response.status} - ${errorText}`);
                console.error(`❌ Response headers:`, Object.fromEntries(response.headers.entries()));
                
                // Send error message back to user
                await this.sendMessage(fromNumber, "Sorry, I couldn't process your audio message. Please try sending a text message instead.");
                return;
            }
            
            console.log(`📄 Step 5: Parsing response...`);
            const result = await response.json();
            console.log(`✅ Speech-to-text successful:`);
            console.log(`   Transcript: "${result.transcript}"`);
            console.log(`   AI Response: "${result.ai_response?.substring(0, 100)}..."`);
            
            // Send AI response back to WhatsApp user
            // Note: Transcript is already processed and saved by the FastAPI /speech-to-text endpoint
            // No need to save transcript again here to avoid duplication loops
            if (result.ai_response && result.ai_response.trim()) {
                await this.sendMessage(fromNumber, result.ai_response);
                console.log(`✅ AI response sent back to WhatsApp user`);
            } else {
                console.log(`⚠️ Empty AI response, not sending message`);
            }
            
            console.log(`===== END AUDIO MESSAGE PROCESSING =====`);
            
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error processing audio message:`, error);
            console.error(`❌ Error type: ${error.constructor.name}`);
            console.error(`❌ Error message: ${error.message}`);
            console.error(`❌ Error stack:`, error.stack);
            
            // Detailed error analysis
            let errorDetails = "Unknown error";
            let userMessage = "Sorry, I encountered an error processing your audio message. Please try again or send a text message.";
            
            if (error.message?.includes('form-data')) {
                errorDetails = "FormData/multipart upload error";
                console.error(`🔧 SOLUTION: Install form-data package: npm install form-data`);
            } else if (error.message?.includes('fetch') || error.message?.includes('ECONNREFUSED')) {
                errorDetails = "Network/API connection error";
                console.error(`🔧 SOLUTION: Check FASTAPI_URL environment variable and FastAPI service status`);
            } else if (error.message?.includes('OpenAI') || error.message?.includes('API key')) {
                errorDetails = "OpenAI API configuration error";
                console.error(`🔧 SOLUTION: Check OPENAI_API_KEY environment variable`);
            } else if (error.message?.includes('downloadMediaMessage')) {
                errorDetails = "WhatsApp media download error";
                console.error(`🔧 SOLUTION: Check WhatsApp connection and media permissions`);
            } else if (error.message?.includes('audio') || error.message?.includes('format')) {
                errorDetails = "Audio format/processing error";
                console.error(`🔧 SOLUTION: Check audio file format and size`);
            }
            
            console.error(`❌ Error category: ${errorDetails}`);
            console.error(`❌ Environment check:`);
            console.error(`   FASTAPI_URL: ${process.env.FASTAPI_URL || 'NOT SET'}`);
            console.error(`   OPENAI_API_KEY: ${process.env.OPENAI_API_KEY ? 'SET' : 'NOT SET'}`);
            console.error(`   WhatsApp status: ${this.status}`);
            
            // Send error message to user
            try {
                await this.sendMessage(fromNumber, userMessage);
            } catch (sendError) {
                console.error(`❌ Failed to send error message:`, sendError);
            }
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

    async saveTranscriptAsClientMessage(fromNumber, transcript, originalMessageId) {
        try {
            console.log(`💾 ===== SAVING TRANSCRIPT AS CLIENT MESSAGE =====`);
            console.log(`📱 From: ${fromNumber}`);
            console.log(`💬 Transcript: "${transcript}"`);
            console.log(`🔗 Session ID: ${this.sessionId}`);
            
            const fastApiUrl = process.env.FASTAPI_URL || 'http://localhost:8000';
            const response = await fetch(`${fastApiUrl}/whatsapp/incoming`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    from_number: fromNumber,
                    message: transcript,
                    session_id: this.sessionId,
                    message_id: `transcript_${originalMessageId}`, // Unique ID for transcript
                    timestamp: new Date().toISOString(),
                    chat_id: fromNumber + '@s.whatsapp.net',
                    is_transcript: true // Flag to indicate this is a transcribed message
                })
            });

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`❌ [${this.sessionId}] Failed to save transcript: ${response.status} - ${errorText}`);
            } else {
                console.log(`✅ [${this.sessionId}] Transcript saved successfully as client message`);
            }
            
            console.log(`===== END TRANSCRIPT SAVING =====`);
            
        } catch (error) {
            console.error(`❌ [${this.sessionId}] Error saving transcript:`, error);
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

        if (refresh || !session.qrCode) {
            await session.connect();
        }

        const qrImage = await session.getQRCode();
        if (!qrImage) {
            return res.status(404).json({ 
                success: false, 
                error: 'QR code not available. Session may be connected or failed.',
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
        console.error('❌ QR code error:', error);
        res.status(500).json({ 
            success: false, 
            error: `QR code generation failed: ${error.message}` 
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
                session_id: sessionId,
                status: 'not_found',
                connected: false,
                qr_available: false,
                last_seen: null,
                has_auth: false
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
                error: 'Session not found. Please create a session first.' 
            });
        }

        if (session.status !== 'connected') {
            return res.status(400).json({ 
                success: false, 
                error: `Session not connected. Current status: ${session.status}` 
            });
        }

        const result = await session.sendMessage(to, message);
        
        res.json({
            success: true,
            message: 'Message sent successfully',
            session_id: session_id,
            to: to,
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
        
        if (!session) {
            return res.status(404).json({ 
                success: false, 
                error: 'Session not found' 
            });
        }

        await session.cleanup();
        sessions.delete(sessionId);

        res.json({
            success: true,
            message: 'Session deleted successfully',
            session_id: sessionId
        });

    } catch (error) {
        console.error('❌ Session deletion error:', error);
        res.status(500).json({ 
            success: false, 
            error: `Session deletion failed: ${error.message}` 
        });
    }
});

/**
 * Auto-restore all sessions from database on startup
 */
async function autoRestoreAllSessions() {
    try {
        console.log('🔄 Auto-restoring all sessions from database...');
        
        const client = await pool.connect();
        const result = await client.query('SELECT session_id FROM whatsapp_sessions');
        client.release();
        
        if (result.rows.length === 0) {
            console.log('📭 No sessions found in database to restore');
            return;
        }
        
        console.log(`📦 Found ${result.rows.length} sessions to restore:`);
        
        for (const row of result.rows) {
            const sessionId = row.session_id;
            console.log(`🔄 Auto-restoring session: ${sessionId}`);
            
            try {
                // Create session instance
                const session = new WhatsAppSession(sessionId);
                sessions.set(sessionId, session);
                
                // Start connection in background (don't wait)
                session.connect().then(() => {
                    console.log(`✅ Auto-restored session: ${sessionId}`);
                }).catch((error) => {
                    console.error(`❌ Failed to auto-restore session ${sessionId}:`, error);
                });
                
            } catch (error) {
                console.error(`❌ Error creating session ${sessionId}:`, error);
            }
        }
        
        console.log('🚀 Auto-restoration process initiated for all sessions');
        
    } catch (error) {
        console.error('❌ Error during auto-restoration:', error);
    }
}

// Start server
const PORT = process.env.WHATSAPP_PORT || 8002;
app.listen(PORT, '0.0.0.0', async () => {
    console.log(`🚀 WhatsApp service running on port ${PORT}`);
    console.log(`📁 Sessions directory: ${SESSIONS_DIR}`);
    console.log(`🔑 API Key: ${API_KEY.substring(0, 8)}...`);
    console.log(`💾 Database backup enabled: ${!!process.env.DATABASE_URL}`);
    
    // Auto-restore all sessions from database
    setTimeout(autoRestoreAllSessions, 2000); // Wait 2 seconds for service to fully start
});

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('\n🛑 Shutting down WhatsApp service...');
    
    // Cleanup all sessions
    for (const [sessionId, session] of sessions) {
        try {
            await session.cleanup();
        } catch (error) {
            console.error(`❌ Error cleaning up session ${sessionId}:`, error);
        }
    }
    
    // Close database pool
    try {
        await pool.end();
    } catch (error) {
        console.error('❌ Error closing database pool:', error);
    }
    
    console.log('✅ WhatsApp service shut down gracefully');
    process.exit(0);
});

