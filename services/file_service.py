"""
File handling service for image uploads.
"""

import os
import shutil
import uuid
from pathlib import Path
from typing import Optional
from fastapi import UploadFile, HTTPException

# Configure upload directory
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Allowed image extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    # Check file extension
    ext = Path(file.filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400, 
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check file size
    file.file.seek(0, 2)  # Move to end of file
    file_size = file.file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE / 1024 / 1024}MB"
        )


async def save_upload_file(upload_file: UploadFile, subfolder: str = "menu") -> str:
    """
    Save uploaded file and return the URL path.
    
    Args:
        upload_file: The uploaded file
        subfolder: Subfolder within uploads directory
        
    Returns:
        URL path to access the file (e.g., "/uploads/menu/uuid_filename.jpg")
    """
    validate_image_file(upload_file)
    
    # Create subfolder if it doesn't exist
    folder_path = UPLOAD_DIR / subfolder
    folder_path.mkdir(exist_ok=True)
    
    # Generate unique filename
    ext = Path(upload_file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{ext}"
    file_path = folder_path / unique_filename
    
    # Save file
    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(upload_file.file, buffer)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
    finally:
        upload_file.file.close()
    
    # Return URL path
    return f"/uploads/{subfolder}/{unique_filename}"


def delete_upload_file(file_url: str) -> bool:
    """
    Delete an uploaded file given its URL.
    
    Args:
        file_url: URL path of the file (e.g., "/uploads/menu/uuid_filename.jpg")
        
    Returns:
        True if file was deleted, False if file didn't exist
    """
    if not file_url or not file_url.startswith("/uploads/"):
        return False
    
    # Convert URL to file path
    relative_path = file_url.lstrip("/")
    file_path = Path(relative_path)
    
    if file_path.exists() and file_path.is_file():
        try:
            file_path.unlink()
            return True
        except Exception:
            pass
    
    return False