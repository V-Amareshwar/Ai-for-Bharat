"""
DidiGov — Voice Transcription Router

Endpoint:
    POST /api/v1/voice/transcribe
        Accepts an audio file upload, sends it to Groq Whisper
        with multi-key fallback, and returns the transcribed text.
"""

import logging
from fastapi import APIRouter, File, Form, UploadFile, HTTPException
from fastapi.responses import JSONResponse

from models.voice import TranscribeResponse
from services.groq_client import get_groq_client
from services.translation import translate_to_english, standardize_language_code

logger = logging.getLogger("didi.voice")
router = APIRouter()


@router.post(
    "/transcribe",
    response_model=TranscribeResponse,
    summary="Transcribe audio to text (Groq Whisper AI)",
    description=(
        "Upload an audio file (webm/wav/mp3/ogg/flac). "
        "Returns the transcribed text with detected language using Groq Whisper AI."
    ),
)
async def transcribe_audio(
    audio: UploadFile = File(..., description="Audio file from the browser microphone"),
    language: str = Form(
        default=None,
        description="Optional BCP-47 language hint.",
    ),
):
    """
    Receives a browser audio recording and returns the Groq Whisper transcription.
    """
    # ── Validate file type ─────────────────────────────────────────────────────
    content_type = audio.content_type or "application/octet-stream"
    base_type = content_type.split(";")[0].strip()

    allowed_types = {
        "audio/webm", "video/webm", "audio/wav", "audio/mpeg",
        "audio/mp3", "audio/mp4", "audio/ogg", "audio/flac",
        "audio/x-wav", "application/octet-stream",
    }
    
    if base_type not in allowed_types:
        raise HTTPException(
            status_code=415,
            detail=f"Unsupported audio type: {content_type}. "
                   f"Supported base types: webm, wav, mp3, ogg, flac.",
        )

    # ── Read audio bytes ───────────────────────────────────────────────────────
    audio_bytes = await audio.read()
    if len(audio_bytes) == 0:
        raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")

    file_size_kb = len(audio_bytes) / 1024
    logger.info(
        f"Received audio: filename={audio.filename!r}, "
        f"content_type={content_type}, size={file_size_kb:.1f} KB"
    )
    
    # DEBUG: Save the exact byte stream to disk to diagnose Deepgram's 400 error
    with open("debug_browser_audio.webm", "wb") as f:
        f.write(audio_bytes)

    # ── Transcribe via Groq Whisper ────────────────────────────────────────────
    try:
        import asyncio
        client = get_groq_client()
        result = await asyncio.to_thread(
            client.transcribe,
            audio_data=audio_bytes,
            filename=audio.filename or "recording.webm",
            language=language or None,
        )
        model_used = "groq/whisper-large-v3"
    except ValueError as e:
        # No api keys
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        logger.exception(f"Groq Whisper AI failed: {e}")
        # Pass the 503 HTTP status explicitly to the frontend so it shows the error
        raise HTTPException(
            status_code=503,
            detail=str(e),
        )

    text = result.get("text", "").strip()
    detected_lang = result.get("language") # Whisper's native detection
    duration = result.get("duration")

    # ── Phase 2: Detect Language and Translate ──────────────────────────────────
    # We now trust Whisper's acoustic detection completely. If the user passed
    # an explicit language from the UI, Whisper uses it, otherwise Whisper auto-guesses.
    iso_language = standardize_language_code(detected_lang)
    english_text = translate_to_english(text, source_lang=iso_language)

    logger.info(
        f"Transcription complete | text={text!r} | "
        f"lang={iso_language} (Whisper: {detected_lang}) | "
        f"english={english_text!r} | duration={duration}s"
    )

    # ── Milestone log (Phase 1/2 test requirement) ──────────────────────────────
    logger.info(f"Detected text: {text}")
    logger.info(f"Detected language: {iso_language}")
    logger.info(f"English translation: {english_text}")

    return TranscribeResponse(
        success=True,
        text=text,
        english_text=english_text,
        user_language=iso_language,
        detected_language=detected_lang,
        duration_seconds=duration,
        model_used=model_used,
        message="Transcription and translation successful",
    )


@router.get("/health", summary="Voice service health check")
async def voice_health():
    """Quick check to confirm the voice service is wired up."""
    from config import settings
    key_count = len(settings.groq_keys_list)
    return {
        "service": "voice",
        "status": "ok" if key_count > 0 else "degraded",
        "groq_keys_configured": key_count,
        "model": settings.groq_whisper_model,
    }
