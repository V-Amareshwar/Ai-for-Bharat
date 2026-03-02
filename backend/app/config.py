import os
from dotenv import load_dotenv

load_dotenv()

# ==========================
# ENV VARIABLES
# ==========================

AWS_REGION = os.getenv("AWS_REGION", "ap-south-1")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "jan-sahayak-audio-bucket")

# ==========================
# MOCK DATABASE (DynamoDB Simulation)
# ==========================

# Simulated Users
mock_users_db = {
    # "mobile_number": { user details }
}

# Simulated Applications
mock_applications_db = {
    # "mobile_number": {
    #     "application_json": {},
    #     "status": "pending" | "approved"
    # }
}