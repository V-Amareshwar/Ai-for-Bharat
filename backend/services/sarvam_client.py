"""
DidiGov — Sarvam AI Speech-to-Text Client

Replaces Groq Whisper for highly accurate Indian Regional Language transcription.
Sarvam natively handles 10 Indian languages.
"""

import logging
from typing import BinaryIO
import requests
from config import settings

logger = logging.getLogger("didi.sarvam_client")

# Use the translate endpoint to automatically output English text if needed,
# or the standard speech-to-text endpoint. We'll stick to speech-to-text
# since we handle translation separately, but Sarvam requires a specific payload.
SARVAM_STT_URL = "https://api.sarvam.ai/speech-to-text-translate"

class SarvamWhisperClient:
    """
    Client for interacting with Sarvam AI's speech-to-text API.
    Designed to be a seamless drop-in replacement for the Groq client.
    """

    def __init__(self):
        self.api_key = settings.sarvam_api_key
        if not self.api_key:
            raise ValueError(
                "No Sarvam API key configured. "
                "Set SARVAM_API_KEY in your .env file."
            )

    def transcribe(
        self,
        audio_data: bytes | BinaryIO,
        filename: str = "audio.wav",
        language: str | None = None,
        prompt: str | None = None,
    ) -> dict:
        """
        Transcribe audio using Sarvam AI.

        Args:
            audio_data: Raw audio bytes or a file-like object.
            filename:   Original filename.
            language:   Optional BCP-47 language hint (ignored by Sarvam as it auto-detects, but kept for interface parity).
            prompt:     Optional prompt to guide transcription.

        Returns:
            dict with keys: text, language
        """
        
        # Prepare multipart form data.
        # Sarvam strict requirement: file must be named 'file' and type must be explicitly assigned.
        files = {
            "file": (filename, audio_data, "audio/wav")
        }

        # Sarvam's speech-to-text-translate endpoint handles translation natively, returning both transcript and translation
        data = {
            "model": "saaras:v1"
        }
        
        if prompt:
            data["prompt"] = prompt

        headers = {
            "api-subscription-key": self.api_key,
            # Let requests build the Content-Type header with the internal boundary
        }

        logger.info(f"Calling Sarvam STT (file={filename}, endpoint={SARVAM_STT_URL})")

        try:
            response = requests.post(
                SARVAM_STT_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=60,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            msg = response.text if response else str(e)
            logger.error(f"Sarvam API Error: {msg}")
            
            # If Sarvam is actually down (503 Service Unavailable), fail gracefully
            if response is not None and response.status_code == 503:
                raise Exception("Sarvam AI STT service is temporarily down (503). Try again later.")
            
            raise Exception(f"Sarvam API failed: {msg}")

        payload = response.json()
        
        # Responses look like: {"transcript": "...", "language_code": "hi-IN"}
        detected_lang = payload.get("language_code", "auto")
        
        return {
            "text": payload.get("transcript", "").strip(),
            "language": detected_lang,
            "duration": None, # Sarvam might not return duration, keeping interface parity
        }

def get_sarvam_client() -> SarvamWhisperClient:
    return SarvamWhisperClient()
