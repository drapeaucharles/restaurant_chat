"""
Smart Lamp audio routes with WebSocket support for real-time audio streaming.
"""
from fastapi import APIRouter, HTTPException, Query, WebSocket, WebSocketDisconnect, Depends
import openai
import os
import requests
import io
import wave
import struct
import uuid
import json
import numpy as np
from typing import List
from sqlalchemy.orm import Session
from datetime import datetime
from pydub import AudioSegment

# Import database and models
from database import get_db
import models
from services.chat_service import get_or_create_client

router = APIRouter(tags=["smartlamp"])

# G.711 μ-law decoding table
ULAW_DECODE_TABLE = np.array([
    -32124,-31100,-30076,-29052,-28028,-27004,-25980,-24956,
    -23932,-22908,-21884,-20860,-19836,-18812,-17788,-16764,
    -15996,-15484,-14972,-14460,-13948,-13436,-12924,-12412,
    -11900,-11388,-10876,-10364, -9852, -9340, -8828, -8316,
    -7932, -7676, -7420, -7164, -6908, -6652, -6396, -6140,
    -5884, -5628, -5372, -5116, -4860, -4604, -4348, -4092,
    -3900, -3772, -3644, -3516, -3388, -3260, -3132, -3004,
    -2876, -2748, -2620, -2492, -2364, -2236, -2108, -1980,
    -1884, -1820, -1756, -1692, -1628, -1564, -1500, -1436,
    -1372, -1308, -1244, -1180, -1116, -1052,  -988,  -924,
    -876,  -844,  -812,  -780,  -748,  -716,  -684,  -652,
    -620,  -588,  -556,  -524,  -492,  -460,  -428,  -396,
    -372,  -356,  -340,  -324,  -308,  -292,  -276,  -260,
    -244,  -228,  -212,  -196,  -180,  -164,  -148,  -132,
    -120,  -112,  -104,   -96,   -88,   -80,   -72,   -64,
    -56,   -48,   -40,   -32,   -24,   -16,    -8,     0,
    32124, 31100, 30076, 29052, 28028, 27004, 25980, 24956,
    23932, 22908, 21884, 20860, 19836, 18812, 17788, 16764,
    15996, 15484, 14972, 14460, 13948, 13436, 12924, 12412,
    11900, 11388, 10876, 10364,  9852,  9340,  8828,  8316,
    7932,  7676,  7420,  7164,  6908,  6652,  6396,  6140,
    5884,  5628,  5372,  5116,  4860,  4604,  4348,  4092,
    3900,  3772,  3644,  3516,  3388,  3260,  3132,  3004,
    2876,  2748,  2620,  2492,  2364,  2236,  2108,  1980,
    1884,  1820,  1756,  1692,  1628,  1564,  1500,  1436,
    1372,  1308,  1244,  1180,  1116,  1052,   988,   924,
    876,   844,   812,   780,   748,   716,   684,   652,
    620,   588,   556,   524,   492,   460,   428,   396,
    372,   356,   340,   324,   308,   292,   276,   260,
    244,   228,   212,   196,   180,   164,   148,   132,
    120,   112,   104,    96,    88,    80,    72,    64,
    56,    48,    40,    32,    24,    16,     8,     0
], dtype=np.int16)


def generate_client_id_from_lamp_id(lamp_id: str) -> str:
    """
    Generate a consistent client ID from smart lamp identifier.
    This ensures the same lamp_id always gets the same client UUID.
    Similar to WhatsApp's phone number to UUID conversion.
    """
    # Create a deterministic UUID from lamp identifier
    namespace = uuid.UUID('6ba7b810-9dad-11d1-80b4-00c04fd430c8')  # Standard namespace UUID
    client_uuid = uuid.uuid5(namespace, f"smartlamp:{lamp_id}")
    return str(client_uuid)


def decode_ulaw(ulaw_bytes: bytes) -> np.ndarray:
    """Decode G.711 μ-law to 16-bit PCM"""
    return ULAW_DECODE_TABLE[np.frombuffer(ulaw_bytes, dtype=np.uint8)]


def pcm_to_ulaw(pcm_val: int) -> int:
    """Encode single PCM sample to μ-law"""
    # Constants
    MULAW_MAX = 0x1FFF
    MULAW_BIAS = 33
    
    # Get the sign and the magnitude
    if pcm_val < 0:
        pcm_val = -pcm_val
        mask = 0x7F
    else:
        mask = 0xFF
    
    # Clip the magnitude
    if pcm_val > MULAW_MAX:
        pcm_val = MULAW_MAX
    
    # Convert to segment number
    pcm_val += MULAW_BIAS
    
    # Find segment
    seg = 0
    for i in range(8):
        if pcm_val <= 0xFF:
            break
        seg += 1
        pcm_val >>= 1
    
    # Combine segment and quantization bits
    if seg >= 8:
        return 0x7F ^ mask
    else:
        uval = (seg << 4) | ((pcm_val >> 4) & 0x0F)
        return uval ^ mask


def encode_pcm_to_ulaw(pcm_data: np.ndarray) -> bytes:
    """Encode 16-bit PCM to G.711 μ-law"""
    ulaw_data = np.zeros(len(pcm_data), dtype=np.uint8)
    for i, sample in enumerate(pcm_data):
        ulaw_data[i] = pcm_to_ulaw(int(sample))
    return ulaw_data.tobytes()


def create_wav_from_pcm(pcm_data: np.ndarray, sample_rate: int = 16000) -> bytes:
    """Create WAV file from PCM samples"""
    wav_buffer = io.BytesIO()
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(1)  # Mono
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_data.tobytes())
    
    wav_buffer.seek(0)
    return wav_buffer.getvalue()


class AudioStreamHandler:
    """Handle audio streaming for a WebSocket connection"""
    
    def __init__(self, websocket: WebSocket, client_id: str, restaurant_id: str, db: Session):
        self.websocket = websocket
        self.client_id = client_id
        self.restaurant_id = restaurant_id
        self.db = db
        self.audio_buffer: List[np.ndarray] = []
        self.is_recording = False
        self.sequence_num = 0
        self.client_uuid = generate_client_id_from_lamp_id(client_id)
        
    async def handle_control_message(self, message: dict):
        """Handle control messages (start_stream, end_stream, heartbeat)"""
        msg_type = message.get("type")
        
        if msg_type == "start_stream":
            print(f"🎙️ Starting audio stream for {self.client_id}")
            self.is_recording = True
            self.audio_buffer = []
            self.sequence_num = 0
            
        elif msg_type == "end_stream":
            print(f"🏁 Ending audio stream for {self.client_id}")
            self.is_recording = False
            
            if self.audio_buffer:
                await self.process_audio()
            else:
                print("⚠️ No audio data received")
                
        elif msg_type == "heartbeat":
            # Respond with heartbeat acknowledgment
            await self.websocket.send_json({
                "type": "heartbeat_ack",
                "timestamp": int(datetime.now().timestamp() * 1000)
            })
            
    async def handle_audio_packet(self, data: bytes):
        """Handle binary audio packet"""
        if not self.is_recording:
            return
            
        if len(data) < 3:
            print("⚠️ Invalid audio packet: too short")
            return
            
        # Parse packet header
        packet_type = data[0]
        sequence = (data[1] << 8) | data[2]
        
        if packet_type != 0x01:
            print(f"⚠️ Unknown packet type: {packet_type}")
            return
            
        # Extract and decode G.711 audio
        ulaw_data = data[3:]
        pcm_data = decode_ulaw(ulaw_data)
        
        self.audio_buffer.append(pcm_data)
        
        # Log progress every 50 packets
        if sequence % 50 == 0:
            total_samples = sum(len(chunk) for chunk in self.audio_buffer)
            duration = total_samples / 16000  # 16kHz sample rate
            print(f"📊 Received packet {sequence}, total audio: {duration:.2f}s")
            
    async def process_audio(self):
        """Process accumulated audio with Whisper and send response"""
        print(f"🎯 Processing audio for {self.client_id}")
        
        try:
            # Concatenate all audio chunks
            pcm_data = np.concatenate(self.audio_buffer)
            total_samples = len(pcm_data)
            duration = total_samples / 16000
            print(f"📊 Total audio: {total_samples} samples ({duration:.2f}s)")
            
            # Create WAV file for Whisper
            wav_data = create_wav_from_pcm(pcm_data)
            
            # Ensure client exists in database
            client = get_or_create_client(self.db, self.client_uuid, self.restaurant_id)
            
            # Transcribe with Whisper
            print("🎯 Transcribing with Whisper...")
            wav_buffer = io.BytesIO(wav_data)
            wav_buffer.name = "audio.wav"  # Whisper needs a filename
            
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=wav_buffer,
                response_format="text"
            )
            
            transcript = transcription.strip()
            print(f"✅ Transcription: '{transcript}'")
            
            if not transcript:
                transcript = "I couldn't understand what you said."
                ai_response = "I'm sorry, I couldn't understand your audio message. Please try speaking again."
            else:
                # Save user message to database
                client_message = models.ChatMessage(
                    restaurant_id=self.restaurant_id,
                    client_id=uuid.UUID(self.client_uuid),
                    sender_type="client",
                    message=transcript
                )
                self.db.add(client_message)
                self.db.commit()
                
                # Get AI response
                print("🤖 Getting AI response...")
                chat_completion = openai.chat.completions.create(
                    model="gpt-3.5-turbo",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are a helpful AI assistant for a smart lamp device. Provide concise, friendly responses suitable for voice interaction. Keep responses under 100 words."
                        },
                        {
                            "role": "user",
                            "content": transcript
                        }
                    ],
                    max_tokens=150,
                    temperature=0.7
                )
                
                ai_response = chat_completion.choices[0].message.content.strip()
                print(f"✅ AI response: '{ai_response}'")
                
                # Save AI response to database
                assistant_message = models.ChatMessage(
                    restaurant_id=self.restaurant_id,
                    client_id=uuid.UUID(self.client_uuid),
                    sender_type="assistant",
                    message=ai_response
                )
                self.db.add(assistant_message)
                self.db.commit()
            
            # Convert response to speech
            await self.send_audio_response(ai_response)
            
        except Exception as e:
            print(f"❌ Error processing audio: {str(e)}")
            # Send error message
            await self.websocket.send_json({
                "type": "error",
                "message": f"Failed to process audio: {str(e)}"
            })
            
    async def send_audio_response(self, text: str):
        """Convert text to speech and send as audio packets"""
        print(f"🎵 Converting to speech: '{text}'")
        
        try:
            # Get ElevenLabs TTS
            eleven_api_key = os.getenv("ELEVEN_API_KEY")
            if not eleven_api_key:
                raise Exception("ElevenLabs API key not configured")
                
            voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
            
            headers = {
                "Accept": "audio/mpeg",
                "Content-Type": "application/json",
                "xi-api-key": eleven_api_key
            }
            
            data = {
                "text": text,
                "model_id": "eleven_monolingual_v1",
                "voice_settings": {
                    "stability": 0.5,
                    "similarity_boost": 0.5
                }
            }
            
            # Get MP3 from ElevenLabs
            response = requests.post(tts_url, json=data, headers=headers, stream=True)
            
            if response.status_code != 200:
                raise Exception(f"TTS failed: {response.status_code}")
                
            # Convert MP3 to PCM
            mp3_data = b""
            for chunk in response.iter_content(chunk_size=1024):
                if chunk:
                    mp3_data += chunk
                    
            # Load MP3 and convert to 16kHz mono
            audio = AudioSegment.from_mp3(io.BytesIO(mp3_data))
            audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
            
            # Get PCM data
            pcm_data = np.frombuffer(audio.raw_data, dtype=np.int16)
            
            # Send start of audio response
            await self.websocket.send_json({
                "type": "audio_start",
                "timestamp": int(datetime.now().timestamp() * 1000)
            })
            
            # Send audio in chunks (20ms frames = 320 samples)
            chunk_size = 320
            sequence = 0
            
            for i in range(0, len(pcm_data), chunk_size):
                chunk = pcm_data[i:i + chunk_size]
                
                # Pad last chunk if needed
                if len(chunk) < chunk_size:
                    chunk = np.pad(chunk, (0, chunk_size - len(chunk)), mode='constant')
                
                # Encode to G.711
                ulaw_data = encode_pcm_to_ulaw(chunk)
                
                # Create packet: [type][seq_high][seq_low][audio_data]
                packet = bytes([0x01, (sequence >> 8) & 0xFF, sequence & 0xFF]) + ulaw_data
                
                # Send binary packet
                await self.websocket.send_bytes(packet)
                
                sequence += 1
                
            # Send end of audio response
            await self.websocket.send_json({
                "type": "audio_end",
                "timestamp": int(datetime.now().timestamp() * 1000)
            })
            
            print(f"✅ Sent {sequence} audio packets")
            
        except Exception as e:
            print(f"❌ Error sending audio response: {str(e)}")
            await self.websocket.send_json({
                "type": "error",
                "message": f"Failed to generate audio response: {str(e)}"
            })


@router.websocket("/smartlamp/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str = Query(..., description="Smart lamp identifier"),
    restaurant_id: str = Query(..., description="Restaurant ID"),
    db: Session = Depends(get_db)
):
    """
    WebSocket endpoint for smart lamp real-time audio streaming.
    
    Protocol:
    1. Client connects with ?client_id=xxx&restaurant_id=xxx
    2. Client sends control messages (JSON):
       - {"type": "start_stream", "client_id": "xxx", "timestamp": xxx}
       - {"type": "end_stream", "client_id": "xxx", "timestamp": xxx}
       - {"type": "heartbeat", "client_id": "xxx", "timestamp": xxx}
    3. Client sends audio packets (binary):
       - [0x01][seq_high][seq_low][g711_audio_data...]
    4. Server processes audio on "end_stream" and sends response
    5. Server sends audio response as binary packets with same format
    
    ESP32 WebSocket URL:
    wss://restaurantchat-production.up.railway.app/smartlamp/ws?client_id=lampe1&restaurant_id=RestoLorenzo
    """
    
    print(f"\n🔌 ===== WEBSOCKET CONNECTION REQUEST =====")
    print(f"👤 Client ID: {client_id}")
    print(f"🏪 Restaurant ID: {restaurant_id}")
    
    # Validate restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    
    if not restaurant:
        print(f"❌ Restaurant not found: {restaurant_id}")
        await websocket.close(code=4004, reason=f"Restaurant '{restaurant_id}' not found")
        return
        
    # Accept WebSocket connection
    await websocket.accept()
    print(f"✅ WebSocket connected for {client_id}")
    
    # Create audio handler
    handler = AudioStreamHandler(websocket, client_id, restaurant_id, db)
    
    try:
        # Main message loop
        while True:
            # Receive message (can be text or binary)
            message = await websocket.receive()
            
            if "text" in message:
                # Control message (JSON)
                try:
                    data = json.loads(message["text"])
                    await handler.handle_control_message(data)
                except json.JSONDecodeError:
                    print(f"⚠️ Invalid JSON: {message['text']}")
                    
            elif "bytes" in message:
                # Audio packet (binary)
                await handler.handle_audio_packet(message["bytes"])
                
    except WebSocketDisconnect:
        print(f"📴 WebSocket disconnected for {client_id}")
    except Exception as e:
        print(f"❌ WebSocket error: {str(e)}")
        await websocket.close(code=1011, reason=str(e))
    finally:
        print(f"===== END WEBSOCKET CONNECTION =====\n")