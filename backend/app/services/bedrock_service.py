import boto3
import json
import re
from ..config import AWS_REGION, KNOWLEDGE_BASE_ID

# ==========================================
# THE STATE-MACHINE SYSTEM PROMPT
# ==========================================
SYSTEM_PROMPT = """You are Didi, an official AI digital assistant for the Government.
Your job is to guide citizens through government schemes using the provided JSON data.

<search_results>
$search_results$
</search_results>

User's input: <question>$question$</question>

CORE DIRECTIVES & STATE MACHINE:
You must determine the user's current state based on the conversation and behave accordingly:

STATE 1: EXPLORE (General inquiry & Eligibility)
- If the user asks what a scheme is, summarize its objective and benefits simply.
- Briefly summarize the "eligibility_rules". Do not list them all out mechanically; explain them naturally so a citizen can understand.
- End your response by asking: "Do you meet these criteria, and would you like to apply?"

STATE 2: INTERVIEW (Data Collection)
- If the user wants to apply, look EXACTLY at the "required_user_fields" list in the search results.
- Ask the user for these missing fields ONE AT A TIME. 
- Never overwhelm the user by asking for more than one or two pieces of information in a single response.
- As the user answers, extract their data and map it exactly to the required field names.

STATE 3: REVIEW (Final Submission)
- If you have successfully collected non-null values for EVERY field listed in "required_user_fields", ask for final confirmation.
- Say: "I have all your required details. Should I officially submit your application?"
- If the user says yes, change the "is_ready_to_submit" flag to true.

STRICT OUTPUT FORMAT:
You MUST respond ONLY with a valid JSON object. Absolutely no markdown ticks (```json), no preambles, and no conversational text outside the JSON.

{
  "current_state": "Explore | Interview | Review",
  "speech_response": "The exact words you will speak to the citizen.",
  "extracted_data": {
    "dynamic_field_name_1": "extracted value or null",
    "dynamic_field_name_2": "extracted value or null"
  },
  "is_ready_to_submit": false
}"""

def ask_didi_bedrock(user_query: str, session_id: str = None) -> dict:
    """
    Sends the user's question to the Amazon Bedrock Knowledge Base using a State Machine prompt.
    Returns a dictionary with the structured JSON answer and the session ID.
    """
    client = boto3.client('bedrock-agent-runtime', region_name=AWS_REGION)
    model_id = "amazon.nova-pro-v1:0"

    request_params = {
        'input': {
            'text': user_query
        },
        'retrieveAndGenerateConfiguration': {
            'type': 'KNOWLEDGE_BASE',
            'knowledgeBaseConfiguration': {
                'knowledgeBaseId': KNOWLEDGE_BASE_ID,
                'modelArn': f"arn:aws:bedrock:{AWS_REGION}::foundation-model/{model_id}",
                'generationConfiguration': {
                    'promptTemplate': {
                        'textPromptTemplate': SYSTEM_PROMPT
                    }
                }
            }
        }
    }

    if session_id:
        request_params['sessionId'] = session_id

    try:
        response = client.retrieve_and_generate(**request_params)
        
        raw_text = response['output']['text']
        new_session_id = response['sessionId']
        
        # Safety Net: Strip away any markdown formatting if the LLM disobeys the prompt
        match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        clean_json_str = match.group(0) if match else raw_text
            
        parsed_response = json.loads(clean_json_str)
        
        return {
            "ai_data": parsed_response,
            "session_id": new_session_id
        }

    except Exception as e:
        print(f"Bedrock Error: {e}")
        print(f"Raw Output that caused error: {raw_text if 'raw_text' in locals() else 'None'}")
        
        # Graceful degradation fallback
        fallback = {
            "current_state": "Error",
            "speech_response": "I'm sorry, I am having a little trouble understanding. Could you please repeat that?",
            "extracted_data": {},
            "is_ready_to_submit": False
        }
        return {"ai_data": fallback, "session_id": session_id}