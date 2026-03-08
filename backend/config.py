"""
DidiGov Backend — Configuration
Loads all settings from environment variables (via .env file).
"""

import os
import secrets
from functools import lru_cache
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """
    Centralised settings for the DidiGov backend.
    All values are loaded from environment variables / .env file.
    """

    # ── FastAPI ────────────────────────────────────────────
    api_host: str = Field(default="0.0.0.0", alias="API_HOST")
    api_port: int = Field(default=8000, alias="API_PORT")
    api_reload: bool = Field(default=True, alias="API_RELOAD")
    api_cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000",
        alias="API_CORS_ORIGINS"
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.api_cors_origins.split(",")]

    # ── AWS Core ───────────────────────────────────────────
    aws_access_key_id: str = Field(default="", alias="AWS_ACCESS_KEY_ID")
    aws_secret_access_key: str = Field(default="", alias="AWS_SECRET_ACCESS_KEY")
    aws_region: str = Field(default="ap-south-1", alias="AWS_REGION")

    # ── AWS Bedrock ────────────────────────────────────────
    bedrock_model_id: str = Field(
        default="amazon.nova-pro-v1:0",
        alias="BEDROCK_MODEL_ID"
    )
    bedrock_knowledge_base_id: str = Field(
        default="", alias="BEDROCK_KNOWLEDGE_BASE_ID"
    )
    bedrock_kb_retrieval_results: int = Field(
        default=5, alias="BEDROCK_KB_RETRIEVAL_RESULTS"
    )

    # ── DynamoDB ───────────────────────────────────────────
    dynamodb_users_table: str = Field(
        default="didi_users", alias="DYNAMODB_USERS_TABLE"
    )
    dynamodb_conversations_table: str = Field(
        default="didi_conversations", alias="DYNAMODB_CONVERSATIONS_TABLE"
    )
    dynamodb_applications_table: str = Field(
        default="didi_applications", alias="DYNAMODB_APPLICATIONS_TABLE"
    )

    # ── Amazon Polly ───────────────────────────────────────
    polly_default_voice: str = Field(default="Aditi", alias="POLLY_DEFAULT_VOICE")
    polly_default_engine: str = Field(default="standard", alias="POLLY_DEFAULT_ENGINE")
    polly_default_language: str = Field(default="hi-IN", alias="POLLY_DEFAULT_LANGUAGE")

    # ── S3 ─────────────────────────────────────────────────
    # REQUIRED: The backend reads scheme JSON files directly from S3 to
    # generate application forms (required_user_fields). This is separate
    # from Bedrock KB retrieval (which handles Q&A). Both are needed.
    s3_schemes_bucket: str = Field(default="", alias="S3_SCHEMES_BUCKET")
    s3_schemes_prefix: str = Field(default="schemes/", alias="S3_SCHEMES_PREFIX")

    # ── Deepgram (Indic Speech-to-Text) ────────────────────
    # High-speed transcription for Indian regional languages
    deepgram_api_key: str = Field(
        default="",
        alias="DEEPGRAM_API_KEY",
        description="Deepgram API Key for nova-2/3 transcription"
    )

    # ── Sarvam AI (Indic Speech-to-Text) ────────────────────
    # Highly accurate model for Indian regional languages
    sarvam_api_key: str = Field(
        default="",
        alias="SARVAM_API_KEY",
        description="Sarvam AI API Key for saaras:v1 transcription"
    )

    # ── Groq (Whisper STT) — Multi-key with fallback ────────
    # Provide multiple keys separated by commas to avoid rate-limit failures.
    # The GroqClient will rotate through them sequentially / randomly.
    groq_api_keys: str = Field(
        default="",
        alias="GROQ_API_KEYS",
        description="Comma-separated list of Groq API keys. e.g. key1,key2,key3"
    )
    groq_whisper_model: str = Field(
        default="whisper-large-v3", alias="GROQ_WHISPER_MODEL"
    )

    @property
    def groq_keys_list(self) -> list[str]:
        """Returns the parsed, non-empty list of Groq API keys."""
        return [k.strip() for k in self.groq_api_keys.split(",") if k.strip()]

    # ── Security / JWT ─────────────────────────────────────
    # Used for: session tokens, user identification, API security.
    # Generate a strong random key: python -c "import secrets; print(secrets.token_hex(32))"
    jwt_secret_key: str = Field(
        default="change-me-in-production",
        alias="JWT_SECRET_KEY"
    )
    jwt_algorithm: str = Field(default="HS256", alias="JWT_ALGORITHM")
    jwt_expire_hours: int = Field(default=24, alias="JWT_EXPIRE_HOURS")

    # ── Session ────────────────────────────────────────────
    session_ttl_hours: int = Field(default=24, alias="SESSION_TTL_HOURS")
    max_conversation_history: int = Field(
        default=20, alias="MAX_CONVERSATION_HISTORY"
    )

    model_config = {
        "env_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        "env_file_encoding": "utf-8",
        "extra": "ignore"
    }


@lru_cache()
def get_settings() -> Settings:
    """
    Returns a cached Settings instance.
    Use this as a FastAPI dependency: Depends(get_settings)
    """
    return Settings()


# Convenience singleton for non-DI usage
settings = get_settings()
