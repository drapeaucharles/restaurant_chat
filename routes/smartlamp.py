"""
Smart Lamp audio routes for handling voice interactions.
"""
from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
import openai
import tempfile
import os
import requests
import io
from typing import Generator

router = APIRouter(tags=["smartlamp"])


@router.post("/smartlamp/audio")
async def smartlamp_audio(
    file: UploadFile = File(...)
):
    """
    Handle Smart Lamp audio input:
    1. Transcribe audio using OpenAI Whisper
    2. Send transcript to OpenAI ChatCompletion
    3. Convert response to speech using ElevenLabs TTS
    4. Return audio stream (mp3) to the smart lamp
    
    This is a standalone endpoint that doesn't interfere with existing chat flows.
    """
    
    print(f"\n🔊 ===== SMART LAMP AUDIO ENDPOINT CALLED =====")
    print(f"📁 File: {file.filename}, Content-Type: {file.content_type}")
    
    # Validate audio file
    if not file.content_type or not file.content_type.startswith('audio/'):
        raise HTTPException(status_code=400, detail="File must be an audio file")
    
    # Supported audio formats for Whisper
    supported_formats = ['.mp3', '.mp4', '.mpeg', '.mpga', '.m4a', '.wav', '.webm', '.ogg']
    file_extension = os.path.splitext(file.filename or '')[1].lower()
    
    if file_extension not in supported_formats:
        raise HTTPException(
            status_code=400, 
            detail=f"Unsupported audio format. Supported formats: {', '.join(supported_formats)}"
        )
    
    transcript = ""
    ai_response = ""
    
    try:
        # Step 1: Transcribe audio with OpenAI Whisper
        print("🎯 Step 1: Starting Whisper transcription...")
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        print(f"💾 Saved audio file temporarily: {temp_file_path}")
        
        # Transcribe with OpenAI Whisper
        with open(temp_file_path, "rb") as audio_file:
            transcription = openai.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                response_format="text"
            )
        
        transcript = transcription.strip()
        print(f"✅ Transcription successful: '{transcript}'")
        
        if not transcript:
            print("⚠️ Empty transcription received")
            transcript = "I couldn't understand what you said."
            ai_response = "I'm sorry, I couldn't understand your audio message. Please try speaking again."
        else:
            # Step 2: Send transcript to OpenAI ChatCompletion
            print("🤖 Step 2: Getting AI response from ChatGPT...")
            
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
        
        # Step 3: Convert response to speech using ElevenLabs TTS
        print("🎵 Step 3: Converting response to speech with ElevenLabs...")
        
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
        
        # Step 4: Stream the audio response back to the smart lamp
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

