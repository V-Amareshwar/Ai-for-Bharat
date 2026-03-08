"""
DidiGov — DynamoDB Table Provisioning Script
Run this ONCE to create all required DynamoDB tables in your AWS account.

Usage:
    python setup_dynamodb.py              # Create tables
    python setup_dynamodb.py --dry-run   # Print config only, don't create
    python setup_dynamodb.py --delete    # Delete tables (DANGER!)
"""

import sys
import os
import json
import logging
import argparse
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv

# Load .env from project root
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
load_dotenv(os.path.join(root_dir, ".env"))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("didi.setup")

# ── Table Definitions ──────────────────────────────────────────────────────────

TABLES = [
    {
        "TableName": "didi_users",
        "KeySchema": [
            {"AttributeName": "mobile_number", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "mobile_number", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",  # No capacity planning needed
        "Tags": [
            {"Key": "Project", "Value": "DidiGov"},
            {"Key": "Environment", "Value": "production"},
        ],
    },
    {
        "TableName": "didi_conversations",
        "KeySchema": [
            {"AttributeName": "session_id", "KeyType": "HASH"},
            {"AttributeName": "timestamp", "KeyType": "RANGE"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "session_id", "AttributeType": "S"},
            {"AttributeName": "timestamp", "AttributeType": "S"},
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "DidiGov"},
            {"Key": "Environment", "Value": "production"},
        ],
    },
    {
        "TableName": "didi_applications",
        "KeySchema": [
            {"AttributeName": "application_id", "KeyType": "HASH"},
        ],
        "AttributeDefinitions": [
            {"AttributeName": "application_id", "AttributeType": "S"},
            {"AttributeName": "mobile_number", "AttributeType": "S"},
        ],
        "GlobalSecondaryIndexes": [
            {
                "IndexName": "mobile_number-index",
                "KeySchema": [
                    {"AttributeName": "mobile_number", "KeyType": "HASH"},
                ],
                "Projection": {"ProjectionType": "ALL"},
            }
        ],
        "BillingMode": "PAY_PER_REQUEST",
        "Tags": [
            {"Key": "Project", "Value": "DidiGov"},
            {"Key": "Environment", "Value": "production"},
        ],
    },
]


# ── Helpers ────────────────────────────────────────────────────────────────────

def get_client(region: str):
    """Create a DynamoDB client. Uses default credential chain (AWS CLI / env vars)."""
    return boto3.client("dynamodb", region_name=region)


def table_exists(client, table_name: str) -> bool:
    try:
        client.describe_table(TableName=table_name)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return False
        raise


def create_table(client, table_def: dict):
    table_name = table_def["TableName"]
    if table_exists(client, table_name):
        logger.warning(f"  ⚠️  Table '{table_name}' already exists — skipping.")
        return

    logger.info(f"  Creating table '{table_name}' ...")
    try:
        client.create_table(**table_def)
        # Wait until table is active
        waiter = client.get_waiter("table_exists")
        waiter.wait(TableName=table_name)
        logger.info(f"  ✅ Table '{table_name}' created successfully.")
    except ClientError as e:
        logger.error(f"  ❌ Failed to create '{table_name}': {e}")
        raise


def delete_table(client, table_name: str):
    if not table_exists(client, table_name):
        logger.warning(f"  ⚠️  Table '{table_name}' does not exist — skipping.")
        return
    logger.warning(f"  🗑️  Deleting table '{table_name}' ...")
    client.delete_table(TableName=table_name)
    waiter = client.get_waiter("table_not_exists")
    waiter.wait(TableName=table_name)
    logger.info(f"  ✅ Table '{table_name}' deleted.")


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="DidiGov DynamoDB Setup")
    
    # Check .env for the region, fallback to us-east-1 if missing
    default_region = os.environ.get("AWS_REGION", "us-east-1")
    
    parser.add_argument(
        "--region", default=default_region, help=f"AWS region (default: {default_region} from .env)"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print table configs without creating anything",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="DELETE all DidiGov tables (DESTRUCTIVE!)",
    )
    args = parser.parse_args()

    if args.dry_run:
        logger.info("=== DRY RUN — No tables will be created ===")
        for t in TABLES:
            logger.info(f"\nTable: {t['TableName']}")
            logger.info(json.dumps(t, indent=2))
        return

    client = get_client(args.region)
    logger.info(f"Connected to DynamoDB in region: {args.region}")

    if args.delete:
        logger.warning("⚠️  DELETE MODE — This will destroy all DidiGov tables!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.strip().lower() != "yes":
            logger.info("Aborted.")
            return
        for t in TABLES:
            delete_table(client, t["TableName"])
        logger.info("All tables deleted.")
        return

    logger.info("Creating DidiGov DynamoDB tables...\n")
    for table_def in TABLES:
        create_table(client, table_def)

    logger.info("\n🎉 All DynamoDB tables are ready!")
    logger.info("Tables created:")
    for t in TABLES:
        logger.info(f"  - {t['TableName']}")


if __name__ == "__main__":
    main()
