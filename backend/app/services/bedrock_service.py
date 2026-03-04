import boto3
from ..config import AWS_REGION, KNOWLEDGE_BASE_ID

def ask_didi_bedrock(user_query: str) -> str:
    """
    Sends the user's question to the Amazon Bedrock Knowledge Base using Amazon Nova Pro.
    Returns the clean text answer.
    """
    # Connect to the Bedrock Agent Runtime
    client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
    
    # The exact ARN for Amazon Nova Pro
    model_arn = "arn:aws:bedrock:ap-south-1::foundation-model/amazon.nova-pro-v1:0"

    try:
        response = client.retrieve_and_generate(
            input={
                'text': user_query
            },
            retrieveAndGenerateConfiguration={
                'type': 'KNOWLEDGE_BASE',
                'knowledgeBaseConfiguration': {
                    'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                    'modelArn': model_arn
                }
            }
        )
        
        # Extract and return the final clean answer
        final_answer = response['output']['text']
        return final_answer

    except Exception as e:
        print(f"Bedrock Error: {e}")
        return "SYSTEM_ERROR_PLEASE_TRY_AGAIN"