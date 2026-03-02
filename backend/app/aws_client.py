import boto3
from .config import AWS_REGION


# ==========================
# AWS CLIENT INITIALIZATION
# ==========================

transcribe_client = boto3.client("transcribe", region_name=AWS_REGION)
polly_client = boto3.client("polly", region_name=AWS_REGION)
bedrock_runtime = boto3.client(
    "bedrock-agent-runtime",
    region_name=AWS_REGION
)


# ==========================
# WRAPPER FUNCTIONS
# ==========================

def synthesize_speech(text: str) -> bytes:
    response = polly_client.synthesize_speech(
        Text=text,
        OutputFormat="mp3",
        VoiceId="Aditi"
    )

    return response["AudioStream"].read()


def query_bedrock_knowledge_base(user_query: str) -> dict:
    """
    This is a simplified RAG-style call.
    In production, you'd use retrieve_and_generate().
    """

    response = bedrock_runtime.retrieve_and_generate(
        input={"text": user_query},
        retrieveAndGenerateConfiguration={
            "knowledgeBaseConfiguration": {
                "knowledgeBaseId": "YOUR_KB_ID",
                "modelArn": "anthropic.claude-3-sonnet-20240229-v1:0"
            }
        }
    )

    return response