"""
Smart Lamp audio routes for handling voice interactions.
"""
from fastapi import APIRouter, HTTPException, Request, Query
from fastapi.responses import StreamingResponse
import openai
import tempfile
import os
import requests
import io
import wave
import struct
import uuid
import hashlib
from typing import Generator
from sqlalchemy.orm import Session
from fastapi import Depends

# Import database and models
from database import get_db
import models
from services.chat_service import get_or_create_client

router = APIRouter(tags=["smartlamp"])


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


def parse_txt_to_wav(txt_content: str) -> bytes:
    """
    Parse .txt file with audio samples and convert to 16-bit mono 16kHz WAV.
    
    Expected format:
    --- START OF RECORDING ---
    2198
    1950
    1598
    ...
    === END OF DATA ===
    """
    lines = txt_content.strip().split('\n')
    
    # Find start and end markers
    start_idx = None
    end_idx = None
    
    for i, line in enumerate(lines):
        line = line.strip()
        if line == "--- START OF RECORDING ---":
            start_idx = i + 1
        elif line == "=== END OF DATA ===":
            end_idx = i
            break
    
    if start_idx is None:
        raise ValueError("Could not find '--- START OF RECORDING ---' marker in txt file")
    
    if end_idx is None:
        raise ValueError("Could not find '=== END OF DATA ===' marker in txt file")
    
    # Extract and parse sample values
    samples = []
    for i in range(start_idx, end_idx):
        line = lines[i].strip()
        if line:  # Skip empty lines
            try:
                sample = int(line)
                # Clamp to 16-bit signed integer range
                sample = max(-32768, min(32767, sample))
                samples.append(sample)
            except ValueError:
                print(f"⚠️ Skipping invalid sample line: '{line}'")
                continue
    
    if not samples:
        raise ValueError("No valid audio samples found in txt file")
    
    print(f"📊 Parsed {len(samples)} audio samples from txt file")
    
    # Create WAV file in memory
    wav_buffer = io.BytesIO()
    
    # WAV parameters
    sample_rate = 16000  # 16kHz
    channels = 1         # Mono
    sample_width = 2     # 16-bit (2 bytes per sample)
    
    with wave.open(wav_buffer, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        
        # Convert samples to bytes (16-bit signed integers, little-endian)
        audio_data = b''.join(struct.pack('<h', sample) for sample in samples)
        wav_file.writeframes(audio_data)
    
    wav_buffer.seek(0)
    wav_bytes = wav_buffer.getvalue()
    
    print(f"✅ Created WAV file: {len(wav_bytes)} bytes, {len(samples)} samples, 16kHz mono")
    
    return wav_bytes


@router.post("/smartlamp/audio")
async def smartlamp_audio(
    request: Request,
    client_id: str = Query(..., description="Smart lamp identifier (will be converted to UUID)"),
    restaurant_id: str = Query(..., description="Restaurant ID"),
    db: Session = Depends(get_db)
):
    """
    Handle Smart Lamp audio input with simplified interface for ESP32:
    - Accept client_id and restaurant_id as query parameters
    - Accept audio data as plain text in request body (Content-Type: text/plain)
    - Process text with audio samples (convert to WAV) or handle as needed
    
    Processing pipeline:
    1. Parse text body with audio samples and convert to WAV
    2. Transcribe audio using OpenAI Whisper
    3. Save transcript as client message to ChatMessage table
    4. Send transcript to OpenAI ChatCompletion
    5. Save AI response as assistant message to ChatMessage table
    6. Convert response to speech using ElevenLabs TTS
    7. Return audio stream (mp3) to the smart lamp
    
    This endpoint saves conversations to the database like WhatsApp integration.
    """
    
    print(f"\n🔊 ===== SMART LAMP AUDIO ENDPOINT CALLED =====")
    print(f"👤 Client ID (lamp): {client_id}")
    print(f"🏪 Restaurant ID: {restaurant_id}")
    
    # Validate restaurant exists
    restaurant = db.query(models.Restaurant).filter(
        models.Restaurant.restaurant_id == restaurant_id
    ).first()
    if not restaurant:
        print(f"❌ Restaurant not found: {restaurant_id}")
        raise HTTPException(status_code=404, detail=f"Restaurant '{restaurant_id}' not found. Please check the restaurant_id parameter.")
    
    print(f"✅ Restaurant found: {restaurant.restaurant_id}")
    
    # Generate consistent UUID from lamp identifier
    client_uuid = generate_client_id_from_lamp_id(client_id)
    print(f"🔄 Generated client UUID from '{client_id}': {client_uuid}")
    
    # Ensure client exists
    print(f"👤 Ensuring client exists...")
    client = get_or_create_client(db, client_uuid, restaurant_id)
    print(f"✅ Client ensured: {client.id}")
    
    # Read request body as text
    try:
        body_bytes = await request.body()
        txt_content = body_bytes.decode('utf-8')
        print(f"📄 Received text body: {len(txt_content)} characters")
        print(f"📄 First 100 chars: {txt_content[:100]}...")
    except Exception as e:
        print(f"❌ Error reading request body: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to read request body: {str(e)}")
    
    # Process the text content as audio samples
    print("📝 Processing text content with audio samples...")
    
    try:
        # Convert txt samples to WAV
        wav_bytes = parse_txt_to_wav(txt_content)
        
        # Save WAV to temporary file for Whisper
        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
            temp_file.write(wav_bytes)
            temp_file_path = temp_file.name
        
        print(f"💾 Saved converted WAV file temporarily: {temp_file_path}")
        
    except Exception as e:
        print(f"❌ Error processing text content: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Failed to process text content: {str(e)}")
    
    transcript = ""
    ai_response = ""
    
    try:
        # Step 1: Transcribe audio with OpenAI Whisper
        print("🎯 Step 1: Starting Whisper transcription...")
        
        # Transcribe with OpenAI Whisper
        with open(temp_file_path, "rb") as audio_file:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        transcript = transcription.strip()
        print(f"✅ Transcription successful: '{transcript}'")
        
        # Step 2: Save transcript as client message to ChatMessage table
        print(f"💾 Saving client message (transcript) to database...")
        
        client_message = models.ChatMessage(
            restaurant_id=restaurant_id,
            client_id=uuid.UUID(client_uuid),  # Use the generated UUID
            sender_type="client",
            message=transcript
        )
        db.add(client_message)
        db.commit()
        db.refresh(client_message)
        print(f"✅ Client message saved to ChatMessage table with ID: {client_message.id}")
        
        if not transcript:
            print("⚠️ Empty transcription received")
            transcript = "I couldn't understand what you said."
            ai_response = "I'm sorry, I couldn't understand your audio message. Please try speaking again."
        else:
            # Step 3: Send transcript to OpenAI ChatCompletion
            print("🤖 Step 3: Getting AI response from ChatGPT...")
            
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
            print(f"✅ AI response received: '{ai_response}'")
        
        # Step 4: Save AI response as assistant message to ChatMessage table
        print(f"💾 Saving assistant message (AI response) to database...")
        
        assistant_message = models.ChatMessage(
            restaurant_id=restaurant_id,
            client_id=uuid.UUID(client_uuid),  # Use the generated UUID
            sender_type="assistant",
            message=ai_response
        )
        db.add(assistant_message)
        db.commit()
        db.refresh(assistant_message)
        print(f"✅ Assistant message saved to ChatMessage table with ID: {assistant_message.id}")
        
        # Step 5: Convert response to speech using ElevenLabs TTS
        print("🎵 Step 5: Converting response to speech with ElevenLabs...")
        
        # Get ElevenLabs API key from environment
        eleven_api_key = os.getenv("ELEVEN_API_KEY")
        if not eleven_api_key:
            raise HTTPException(status_code=500, detail="ElevenLabs API key not configured")
        
        # ElevenLabs TTS streaming endpoint
        # Using a default voice ID (Rachel) - can be made configurable later
        voice_id = "21m00Tcm4TlvDq8ikWAM"  # Rachel voice
        
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}/stream"
        
        headers = {
            "Accept": "audio/mpeg",
            "Content-Type": "application/json",
            "xi-api-key": eleven_api_key
        }
        
        data = {
            "text": ai_response,
            "model_id": "eleven_monolingual_v1",
            "voice_settings": {
                "stability": 0.5,
                "similarity_boost": 0.5
            }
        }
        
        # Make request to ElevenLabs
        tts_response = requests.post(tts_url, json=data, headers=headers, stream=True)
        
        if tts_response.status_code != 200:
            print(f"❌ ElevenLabs TTS failed: {tts_response.status_code} - {tts_response.text}")
            raise HTTPException(status_code=500, detail="Text-to-speech conversion failed")
        
        print("✅ TTS conversion successful, streaming audio response...")
        
        # Step 6: Stream the audio response back to the smart lamp
        def generate_audio() -> Generator[bytes, None, None]:
            for chunk in tts_response.iter_content(chunk_size=1024):
                if chunk:
                    yield chunk
        
        return StreamingResponse(
            generate_audio(),
            media_type="audio/mpeg",
            headers={
                "Content-Disposition": "attachment; filename=response.mp3",
                "Cache-Control": "no-cache"
            }
        )
        
    except Exception as e:
        print(f"❌ Error in Smart Lamp audio processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Smart Lamp audio processing failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
                print(f"🗑️ Cleaned up temporary file: {temp_file_path}")
        except Exception as e:
            print(f"⚠️ Failed to clean up temporary file: {e}")
        
        print(f"===== END SMART LAMP AUDIO ENDPOINT =====\n")

