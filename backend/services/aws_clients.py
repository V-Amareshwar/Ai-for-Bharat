"""
DidiGov — AWS Boto3 Client Factory
Initialises and caches AWS service clients used throughout the backend.
All clients pick up credentials from config.py (which reads .env).
"""

import logging
import boto3
from functools import lru_cache
from botocore.config import Config

from config import settings

logger = logging.getLogger("didi.aws_clients")

# ── Shared retry config for boto3 ──────────────────────────────────────────────
_RETRY_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "adaptive"},
    connect_timeout=5,
    read_timeout=30,
)


def _make_client(service: str, **kwargs):
    """Helper: create a boto3 client with shared credentials & config."""
    return boto3.client(
        service,
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        config=_RETRY_CONFIG,
        **kwargs,
    )


# ── DynamoDB ───────────────────────────────────────────────────────────────────

@lru_cache()
def get_dynamodb_client():
    """Returns a cached DynamoDB low-level client."""
    logger.info("Initialising DynamoDB client")
    return _make_client("dynamodb")


@lru_cache()
def get_dynamodb_resource():
    """Returns a cached DynamoDB resource (higher-level Table interface)."""
    logger.info("Initialising DynamoDB resource")
    return boto3.resource(
        "dynamodb",
        region_name=settings.aws_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        config=_RETRY_CONFIG,
    )


# ── Amazon Polly ───────────────────────────────────────────────────────────────

@lru_cache()
def get_polly_client():
    """Returns a cached Amazon Polly client."""
    logger.info("Initialising Polly client")
    return _make_client("polly")


# ── AWS Bedrock Runtime (model inference) ──────────────────────────────────────

@lru_cache()
def get_bedrock_runtime_client():
    """
    Returns a cached Bedrock Runtime client.
    Note: Bedrock is only available in specific regions.
    Use us-east-1 or your Bedrock-enabled region.
    """
    bedrock_region = settings.aws_region
    logger.info(f"Initialising Bedrock Runtime client in {bedrock_region}")
    return boto3.client(
        "bedrock-runtime",
        region_name=bedrock_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        config=_RETRY_CONFIG,
    )


# ── AWS Bedrock Agent Runtime (Knowledge Base retrieval) ───────────────────────

@lru_cache()
def get_bedrock_agent_runtime_client():
    """
    Returns a cached Bedrock Agent Runtime client.
    Used for Retrieve calls against the Knowledge Base.
    """
    bedrock_region = settings.aws_region
    logger.info(f"Initialising Bedrock Agent Runtime client in {bedrock_region}")
    return boto3.client(
        "bedrock-agent-runtime",
        region_name=bedrock_region,
        aws_access_key_id=settings.aws_access_key_id or None,
        aws_secret_access_key=settings.aws_secret_access_key or None,
        config=_RETRY_CONFIG,
    )


# ── AWS S3 ─────────────────────────────────────────────────────────────────────

@lru_cache()
def get_s3_client():
    """Returns a cached S3 client for reading scheme JSON files."""
    logger.info("Initialising S3 client")
    return _make_client("s3")
