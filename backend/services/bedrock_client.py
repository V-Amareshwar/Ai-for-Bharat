import logging
import json
from config import settings
from services.aws_clients import get_bedrock_agent_runtime_client, get_bedrock_runtime_client

logger = logging.getLogger("didi.bedrock")

def retrieve_scheme_data(query: str) -> str:
    """
    Queries the AWS Bedrock Knowledge Base (backed by OpenSearch) for the given query.
    Returns a concatenated string of the most relevant scheme JSON blocks or documents.
    """
    kb_id = settings.bedrock_knowledge_base_id
    if not kb_id:
        logger.warning("No BEDROCK_KNOWLEDGE_BASE_ID configured. Skipping RAG retrieval.")
        return ""

    try:
        client = get_bedrock_agent_runtime_client()
        response = client.retrieve(
            knowledgeBaseId=kb_id,
            retrievalQuery={'text': query},
            retrievalConfiguration={
                'vectorSearchConfiguration': {
                    'numberOfResults': settings.bedrock_kb_retrieval_results
                }
            }
        )
        
        results = response.get('retrievalResults', [])
        if not results:
            return ""
            
        # Concatenate the text chunks from the vector DB hits
        context_chunks = []
        for match in results:
            content = match.get('content', {}).get('text', '')
            if content:
                context_chunks.append(content)
                
        # Join with double newlines for clear separation in the prompt
        return "\n\n".join(context_chunks)
        
    except Exception as e:
        logger.error(f"Error querying Bedrock Knowledge Base: {str(e)}")
        return ""

from typing import List, Dict, Any

def _format_messages_for_nova(system_prompt: str, messages: List[Dict[str, Any]]) -> dict:
    """
    Constructs the exact JSON payload expected by the Amazon Nova Pro model.
    Maps the generic internal 'role' and 'content' over to Bedrock's schema.
    """
    formatted_messages = []
    
    # We strip the 'timestamp' and just send role + text to Bedrock
    for msg in messages:
        formatted_messages.append({
            "role": msg.get("role", "user"),
            "content": [{"text": msg.get("content", "")}]
        })
        
    return {
        "system": [{"text": system_prompt}],
        "messages": formatted_messages
    }

def generate_response(system_prompt: str, messages: List[Dict[str, Any]], max_tokens: int = 512, temperature: float = 0.3) -> str:
    """
    Invokes the Amazon Nova Pro foundation model via Bedrock Runtime,
    passing the entire conversation history.
    """
    try:
        client = get_bedrock_runtime_client()
        
        body = _format_messages_for_nova(system_prompt, messages)
        
        # Bedrock InvokeModel parameters
        response = client.invoke_model(
            modelId=settings.bedrock_model_id,
            contentType="application/json",
            accept="application/json",
            body=json.dumps(body)
        )
        
        response_body = json.loads(response.get('body').read())
        
        # Amazon Nova structured output extraction
        if "output" in response_body and "message" in response_body["output"]:
            content_blocks = response_body["output"]["message"].get("content", [])
            if content_blocks and "text" in content_blocks[0]:
                return content_blocks[0]["text"]
        
        return "Sorry, I could not generate a response at this time."
        
    except Exception as e:
        logger.error(f"Error calling Bedrock Nova Pro: {str(e)}")
        return "I am currently experiencing technical difficulties connecting to the government database."
