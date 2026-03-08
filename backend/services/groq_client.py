"""
DidiGov — Groq Whisper Client with Multi-Key Fallback

Supports multiple API keys (GROQ_API_KEYS=key1,key2,key3).
On a rate-limit (429) or auth error (401), automatically retries
with the next available key.

Strategy:
- By default uses SEQUENTIAL rotation (predictable, easy to debug).
- Pass strategy="random" to use random key selection per request.
"""

import logging
import random
import time
from enum import Enum
from typing import BinaryIO

import requests

from config import settings

logger = logging.getLogger("didi.groq_client")

# ── Constants ──────────────────────────────────────────────────────────────────

GROQ_WHISPER_URL = "https://api.groq.com/openai/v1/audio/transcriptions"

# HTTP status codes that warrant a key rotation
_ROTATE_ON_STATUS = {429, 401, 403}

# Seconds to wait before retrying after exhausting all keys
_EXHAUSTED_BACKOFF_SECONDS = 2.0


class RotationStrategy(str, Enum):
    SEQUENTIAL = "sequential"
    RANDOM = "random"


# ── Groq Multi-Key Client ──────────────────────────────────────────────────────

class GroqWhisperClient:
    """
    Groq Whisper transcription client with automatic key rotation.

    Usage:
        client = GroqWhisperClient()
        result = client.transcribe(audio_bytes, filename="recording.webm")
    """

    def __init__(self, strategy: RotationStrategy = RotationStrategy.SEQUENTIAL):
        self.strategy = strategy
        self._keys = settings.groq_keys_list
        self._current_index = 0

        if not self._keys:
            raise ValueError(
                "No Groq API keys configured. "
                "Set GROQ_API_KEYS=key1,key2,key3 in your .env file."
            )

        logger.info(
            f"GroqWhisperClient initialised with {len(self._keys)} key(s), "
            f"strategy={self.strategy.value}"
        )

    def _next_key(self) -> str:
        """Return the next key based on the rotation strategy."""
        if self.strategy == RotationStrategy.RANDOM:
            return random.choice(self._keys)
        # Sequential
        key = self._keys[self._current_index % len(self._keys)]
        self._current_index += 1
        return key

    def transcribe(
        self,
        audio_data: bytes | BinaryIO,
        filename: str = "audio.webm",
        language: str | None = None,
        prompt: str | None = None,
    ) -> dict:
        """
        Transcribe audio using Groq Whisper.

        Args:
            audio_data: Raw audio bytes or a file-like object.
            filename:   Original filename (affects MIME type detection by Groq).
            language:   Optional BCP-47 language hint (e.g. "hi", "en").
            prompt:     Optional prompt to guide transcription style.

        Returns:
            dict with keys: text, language, duration (when available)

        Raises:
            RuntimeError: If all keys fail after rotation.
        """
        tried_keys: set[str] = set()
        last_error: Exception | None = None

        while len(tried_keys) < len(self._keys):
            api_key = self._next_key()

            # Skip already-tried keys in this request cycle
            if api_key in tried_keys:
                continue
            tried_keys.add(api_key)

            try:
                result = self._call_api(
                    api_key=api_key,
                    audio_data=audio_data,
                    filename=filename,
                    language=language,
                    prompt=prompt,
                )
                return result

            except Exception as e:
                status = getattr(e, "status_code", None)
                if status in _ROTATE_ON_STATUS:
                    logger.warning(
                        f"Groq key ending ...{api_key[-6:]} returned {status}. "
                        f"Rotating to next key. ({len(tried_keys)}/{len(self._keys)} tried)"
                    )
                    last_error = e
                    continue
                # Non-rotatable HTTP error — raise immediately
                raise

        # All keys exhausted
        logger.error(f"All {len(self._keys)} Groq API key(s) failed.")
        if last_error:
            raise RuntimeError(
                f"All Groq API keys failed after rotation. Last error: {last_error}"
            ) from last_error
        raise RuntimeError("All Groq API keys failed after rotation.")

    def _call_api(
        self,
        api_key: str,
        audio_data: bytes | BinaryIO,
        filename: str,
        language: str | None,
        prompt: str | None,
    ) -> dict:
        """Makes a single Groq Whisper API call."""

        from groq import Groq

        # Build strictly compliant multipart form data (OpenAI format)
        mime = _mime_for(filename)
        
        # Prepare the file tuple
        if isinstance(audio_data, bytes):
            file_tuple = (filename, audio_data, mime)
        elif hasattr(audio_data, "read"):
            file_tuple = (filename, audio_data.read(), mime)
        else:
            file_tuple = (filename, bytes(audio_data), mime)

        logger.debug(
            f"Calling Groq Whisper SDK (model={settings.groq_whisper_model}, "
            f"key=...{api_key[-6:]}, file={filename})"
        )

        try:
            # Init isolated client specifically for this key
            client = Groq(api_key=api_key, max_retries=1, timeout=20.0)
            
            # The SDK handles the precise multi-part formulation natively
            transcription = client.audio.transcriptions.create(
                file=file_tuple,
                model=settings.groq_whisper_model,
                response_format="verbose_json",
                temperature=0.0,
                language=language if language else None,
                prompt=prompt if prompt else None,
            )
            
            # Convert the Pydantic-like object back to our expected dict structure
            payload = transcription.model_dump()
            
        except Exception as e:
            logger.error(f"Groq SDK Error: {e}")
            raise
        return {
            "text": payload.get("text", "").strip(),
            "language": payload.get("language"),
            "duration": payload.get("duration"),
            "segments": payload.get("segments", []),
        }


# ── Helpers ────────────────────────────────────────────────────────────────────

def _mime_for(filename: str) -> str:
    """Return a reasonable MIME type based on file extension."""
    ext = filename.rsplit(".", 1)[-1].lower()
    mime_map = {
        "webm": "audio/webm",
        "mp3": "audio/mpeg",
        "mp4": "audio/mp4",
        "wav": "audio/wav",
        "ogg": "audio/ogg",
        "flac": "audio/flac",
        "m4a": "audio/mp4",
    }
    return mime_map.get(ext, "audio/webm")


# ── Module-level singleton ─────────────────────────────────────────────────────

def get_groq_client(strategy: RotationStrategy = RotationStrategy.SEQUENTIAL) -> GroqWhisperClient:
    """
    Returns a GroqWhisperClient instance.
    Call this inside a route handler or service — not at module load time,
    so that .env is fully loaded first.
    """
    return GroqWhisperClient(strategy=strategy)
