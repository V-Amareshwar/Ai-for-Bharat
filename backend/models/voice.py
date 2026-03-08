"""
DidiGov — Voice Endpoint Pydantic Models
"""

from pydantic import BaseModel
from typing import Optional


class TranscribeResponse(BaseModel):
    """Response returned by the /voice/transcribe endpoint."""
    model_config = {"protected_namespaces": ()}

    success: bool
    text: str                     # Original transcribed text
    english_text: Optional[str] = None    # English translated text
    user_language: Optional[str] = None   # ISO-639-1 language code of user's language
    detected_language: Optional[str] = None # Original Whisper detected language (often internal name)

    duration_seconds: Optional[float] = None
    model_used: str
    message: Optional[str] = None


class TranscribeErrorResponse(BaseModel):
    success: bool = False
    error: str
    detail: Optional[str] = None
