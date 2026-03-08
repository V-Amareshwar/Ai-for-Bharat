"""
DidiGov — Deepgram AI Speech-to-Text Client

Excellent alternative for high-speed transcription with robust Indic language support
using the Nova-3 engine.
"""

import logging
from typing import BinaryIO
import requests
from config import settings

logger = logging.getLogger("didi.deepgram_client")

# Use Deepgram's pre-recorded audio endpoint
DEEPGRAM_STT_URL = "https://api.deepgram.com/v1/listen"

class DeepgramWhisperClient:
    """
    Client for interacting with Deepgram API.
    Designed to be a seamless drop-in replacement for the Groq client.
    """

    def __init__(self):
        self.api_key = settings.deepgram_api_key
        if not self.api_key:
            raise ValueError(
                "No Deepgram API key configured. "
                "Set DEEPGRAM_API_KEY in your .env file."
            )

    def transcribe(
        self,
        audio_data: bytes | BinaryIO,
        filename: str = "audio.wav",
        language: str | None = None,
        prompt: str | None = None,
    ) -> dict:
        """
        Transcribe audio using Deepgram.

        Args:
            audio_data: Raw audio bytes or a file-like object.
            filename:   Original filename (can be used to guess mime).
            language:   Optional BCP-47 language hint.
            prompt:     Optional prompt (not explicitly used in Deepgram REST here, but kept for interface parity).

        Returns:
            dict with keys: text, language
        """
        
        # Deepgram allows passing raw bytes directly in the body (not multipart form).
        # When sending WebM/Opus from the browser, setting the Header `Content-Type: audio/webm`
        # forces parsing, but we must also ensure we don't accidentally ask for a specific
        # encoding rate that clashes with the browser's dynamic opus generation.
        content_type = "audio/webm"
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": content_type
        }
        
        # Build query parameters for Deepgram
        # Using nova-3-general with detect_language=true allows Deepgram to intelligently
        # downgrade to nova-2 or enhanced if the detected language (e.g. Telugu) isn't on nova-3 yet.
        params = {
            "model": "nova-3-general",
            "smart_format": "true",
            "filler_words": "false",
            "detect_language": "true",
        }

        logger.info(f"Calling Deepgram STT (file={filename}, mime={content_type}, params={params})")

        # Send raw bytes directly in data
        try:
            response = requests.post(
                DEEPGRAM_STT_URL,
                headers=headers,
                params=params,
                data=audio_data,
                timeout=60,
            )
            response.raise_for_status()
        except requests.exceptions.HTTPError as e:
            msg = response.text if response is not None else str(e)
            logger.error(f"Deepgram API Error: {msg}")
            raise Exception(f"Deepgram processing failed: {msg}")

        payload = response.json()
        
        # Deepgram responds with a complex JSON structure. Text is deep inside.
        try:
            transcript = payload["results"]["channels"][0]["alternatives"][0]["transcript"]
            detected_lang = payload["results"]["channels"][0].get("detected_language", "auto")
        except (KeyError, IndexError):
            transcript = ""
            detected_lang = "auto"
        
        return {
            "text": transcript.strip(),
            "language": detected_lang,
            "duration": None, # Kept for interface parity
        }

def get_deepgram_client() -> DeepgramWhisperClient:
    return DeepgramWhisperClient()
