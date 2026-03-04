import os
from dotenv import load_dotenv

load_dotenv()

# ==========================
# ENV VARIABLES
# ==========================
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
KNOWLEDGE_BASE_ID = os.getenv("KNOWLEDGE_BASE_ID")
DEBUG_MODE = os.getenv("DEBUG_MODE", "False").lower() in ("true", "1", "t")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# ==========================
# MOCK DATABASE (DynamoDB Simulation)
# ==========================

# Simulated Users
mock_users_db = {}

# Simulated Applications
mock_applications_db = {}