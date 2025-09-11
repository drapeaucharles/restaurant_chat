"""
Speech-to-text routes for handling audio messages.
"""
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
import openai
import tempfile
import os
import uuid
from datetime import datetime
from database import get_db
from schemas.speech import SpeechToTextResponse
from schemas.chat import ChatRequest
# Import the current chat service based on configuration
import os
if os.getenv("USE_RAG", "true").lower() == "true" and os.getenv("RAG_MODE", "optimized") == "optimized":
    from services.rag_chat_optimized import optimized_rag_service as chat_service
else:
    from services.chat_service import chat_service as chat_service
from models import ChatMessage

router = APIRouter(tags=["speech"])


@router.post("/speech-to-text", response_model=SpeechToTextResponse)
async def speech_to_text(
    file: UploadFile = File(...),
    client_id: str = Form(...),
    restaurant_id: str = Form(...),
    table_id: str = Form(None),
    db: Session = Depends(get_db)
):
    """
    Transcribe audio message using OpenAI Whisper and get AI response.
    
    This is a wrapper around the existing chat flow, triggered only for audio messages.
    Text messages continue to use the standard /chat endpoint.
    """
    
    print(f"\n🎤 ===== SPEECH-TO-TEXT ENDPOINT CALLED =====")
    print(f"📨 Audio message from client_id={client_id}, restaurant_id={restaurant_id}")
    print(f"🏷️ Table ID: {table_id or 'WhatsApp (no table)'}")
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
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=file_extension) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        print(f"💾 Saved audio file temporarily: {temp_file_path}")
        
        # Transcribe with OpenAI Whisper
        print("🎯 Starting Whisper transcription...")
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
            return SpeechToTextResponse(
                transcript="",
                ai_response="I couldn't understand the audio message. Please try again or send a text message."
            )
        
        # Convert client_id to UUID for chat service
        try:
            client_uuid = uuid.UUID(client_id)
        except ValueError:
            # If client_id is not a valid UUID, create one from the string
            client_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, client_id)
            print(f"🔄 Converted client_id '{client_id}' to UUID: {client_uuid}")
        
        # Create chat request with transcribed text
        chat_request = ChatRequest(
            restaurant_id=restaurant_id,
            client_id=client_uuid,
            message=transcript,
            sender_type='client'  # Audio messages are always from clients
        )
        
        print(f"🤖 Calling chat service with transcribed text...")
        print(f"🔍 DEBUG: About to save transcript - restaurant_id: {restaurant_id}, client_id: {client_uuid}")
        print(f"🔍 DEBUG: Transcript to save: '{transcript}'")
        
        # CLEAN SOLUTION: Save transcript with 'client_audio' sender type
        # This appears in chat history but NEVER triggers AI processing
        try:
            print(f"💾 Saving transcript as 'client_audio' message (no AI processing)...")
            
            transcript_message = ChatMessage(
                restaurant_id=restaurant_id,
                client_id=client_uuid,
                message=transcript,
                sender_type='client_audio',  # Special type: saves but no AI processing
                timestamp=datetime.utcnow()
            )
            
            db.add(transcript_message)
            db.commit()
            print(f"✅ Transcript saved as 'client_audio' - will appear in chat history without triggering AI")
            
        except Exception as save_error:
            print(f"❌ Failed to save transcript: {save_error}")
            db.rollback()
        
        # THEN: Call chat service with 'client' sender type (this generates AI response)
        print(f"🤖 Now calling chat service for AI response...")
        chat_response = chat_service(chat_request, db)
        ai_response = chat_response.answer
        
        print(f"✅ AI response received: '{ai_response[:100]}...' (length: {len(ai_response)})")
        
    except Exception as e:
        print(f"❌ Error in speech-to-text processing: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Speech processing failed: {str(e)}")
    
    finally:
        # Clean up temporary file
        try:
            if 'temp_file_path' in locals():
                os.unlink(temp_file_path)
                print(f"🗑️ Cleaned up temporary file: {temp_file_path}")
        except Exception as e:
            print(f"⚠️ Failed to clean up temporary file: {e}")
    
    print(f"===== END SPEECH-TO-TEXT ENDPOINT =====\n")
    
    return SpeechToTextResponse(
        transcript=transcript,
        ai_response=ai_response
    )

