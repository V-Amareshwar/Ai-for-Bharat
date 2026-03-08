"""
DidiGov — Health Check Router
Provides a simple liveness endpoint and an AWS connectivity check.
"""

import logging
from datetime import datetime, timezone

import boto3
from botocore.exceptions import NoCredentialsError, ClientError
from fastapi import APIRouter, Depends

from config import Settings, get_settings

logger = logging.getLogger("didi.health")
router = APIRouter()


# ── Liveness ───────────────────────────────────────────────────────────────────

@router.get("/health", summary="Liveness check")
async def health_check():
    """
    Returns a simple OK response to confirm the API is running.
    Use this for load-balancer / uptime checks.
    """
    return {
        "status": "ok",
        "service": "DidiGov API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ── Readiness (AWS connectivity) ───────────────────────────────────────────────

@router.get("/health/aws", summary="AWS connectivity check")
async def aws_health_check(cfg: Settings = Depends(get_settings)):
    """
    Verifies that AWS credentials are configured and reachable.
    Checks STS identity (IAM), DynamoDB table existence, and Polly access.
    """
    results: dict = {}

    # 1. STS — confirm credentials
    try:
        sts = boto3.client(
            "sts",
            region_name=cfg.aws_region,
            aws_access_key_id=cfg.aws_access_key_id or None,
            aws_secret_access_key=cfg.aws_secret_access_key or None,
        )
        identity = sts.get_caller_identity()
        results["iam"] = {
            "status": "ok",
            "account": identity.get("Account"),
            "arn": identity.get("Arn"),
        }
    except NoCredentialsError:
        results["iam"] = {"status": "error", "detail": "No AWS credentials found"}
    except ClientError as e:
        results["iam"] = {"status": "error", "detail": str(e)}

    # 2. DynamoDB — check tables exist
    try:
        ddb = boto3.client(
            "dynamodb",
            region_name=cfg.aws_region,
            aws_access_key_id=cfg.aws_access_key_id or None,
            aws_secret_access_key=cfg.aws_secret_access_key or None,
        )
        tables_to_check = [
            cfg.dynamodb_users_table,
            cfg.dynamodb_conversations_table,
            cfg.dynamodb_applications_table,
        ]
        table_statuses = {}
        for table in tables_to_check:
            try:
                resp = ddb.describe_table(TableName=table)
                table_statuses[table] = resp["Table"]["TableStatus"]
            except ClientError as e:
                table_statuses[table] = f"error: {e.response['Error']['Code']}"
        results["dynamodb"] = {"status": "ok", "tables": table_statuses}
    except Exception as e:
        results["dynamodb"] = {"status": "error", "detail": str(e)}

    # 3. Polly — list lexicons (lightweight check)
    try:
        polly = boto3.client(
            "polly",
            region_name=cfg.aws_region,
            aws_access_key_id=cfg.aws_access_key_id or None,
            aws_secret_access_key=cfg.aws_secret_access_key or None,
        )
        polly.list_lexicons()
        results["polly"] = {"status": "ok"}
    except Exception as e:
        results["polly"] = {"status": "error", "detail": str(e)}

    overall = "ok" if all(v.get("status") == "ok" for v in results.values()) else "degraded"

    return {
        "status": overall,
        "service": "DidiGov API",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "checks": results,
    }
