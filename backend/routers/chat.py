from fastapi import APIRouter, Depends, HTTPException, Body
from typing import Dict, Any, List
from datetime import datetime
import logging

from models.session import ConversationSession, ChatMessage
from routers.dependencies import get_current_session
from services.db_client import update_session, get_user_applications
from services.bedrock_client import retrieve_scheme_data, generate_response
from services.translation import translate_to_language
from services.polly_client import synthesize_speech

logger = logging.getLogger("didi.chat")
router = APIRouter()

# ── Phase 4: Conversation State Machine ────────────────────────────────────────

def handle_idle(session: ConversationSession, user_input: str) -> str:
    """
    State: IDLE
    The user is starting a brand new conversation or has just finished one.
    """
    logger.info(f"[{session.session_id}] State: IDLE -> Processing input: {user_input}")
    
    lowered = user_input.lower()
    
    # 1. Check if they want their application status
    if any(keyword in lowered for keyword in ["status", "check application", "my application", "where is my"]):
        session.state = "STATUS_CHECK"
        logger.info(f"[{session.session_id}] Promoting state from IDLE -> STATUS_CHECK")
        return handle_status_check(session, user_input)
        
    # 2. If they use triggering words, automatically promote them to a discussion
    lowered = user_input.lower()
    trigger_words = [
        "insurance", "scheme", "apply", "kisan", "yojana", "help", 
        "pm", "fund", "money", "tractor", "crop", "pension", "what is", "tell me"
    ]
    
    if any(keyword in lowered for keyword in trigger_words) or len(lowered.split()) > 3:
        session.state = "SCHEME_DISCUSSION"
        logger.info(f"[{session.session_id}] Promoting state from IDLE -> SCHEME_DISCUSSION")
        
        # Rather than return a static string, we pass the user's initial prompt directly into the discussion router
        # so they get an immediate, factual RAG answer based on their first message.
        return handle_scheme_discussion(session, user_input)
    
    # Still just saying Hello or a very short non-scheme greeting
    system_prompt = "You are Didi, a helpful and friendly government assistant for Indian farmers. Answer this standard greeting politely in 1 short sentence. If it seems they need help, ask how you can assist them with government schemes today."
    
    # Pass the full history up to this point
    history_dicts = [m.dict() for m in session.messages]
    response = generate_response(system_prompt=system_prompt, messages=history_dicts)
    return response

def handle_scheme_discussion(session: ConversationSession, user_input: str) -> str:
    """
    State: SCHEME_DISCUSSION
    The user is asking questions about schemes. We use RAG to answer them
    factually before they decide to apply.
    """
    logger.info(f"[{session.session_id}] State: SCHEME_DISCUSSION -> Processing input: {user_input}")
    lowered = user_input.lower()
    
    # 1. Check for Status update intercept
    if "status" in lowered or "check my application" in lowered or "my application" in lowered:
        session.state = "STATUS_CHECK"
        logger.info(f"[{session.session_id}] Intercepted STATUS_CHECK intent during scheme discussion.")
        return handle_status_check(session, user_input)
    
    # 2. Check if they explicitly want to start the form
    if "apply" in lowered or "form" in lowered or "start" in lowered:
        # Identify WHICH scheme they want to apply for based on the chat history
        history_text = "\n".join([f"{m.role}: {m.content}" for m in session.messages])
        scheme_detection_prompt = f"""Review the following conversation history.
<history>
{history_text}
</history>
What is the specific name of the government scheme the user wants to apply for? 
(For example: PM Kisan, PMJAY, Ayushman Bharat, etc).
Respond WITH ONLY THE EXACT SCHEME NAME. No extra words."""
        
        try:
            detected_scheme = generate_response(
                system_prompt=scheme_detection_prompt,
                messages=[{"role": "user", "content": "Extract the scheme name."}]
            ).strip()
            session.form_data["_active_schema"] = detected_scheme
            logger.info(f"[{session.session_id}] Detected intent to apply for scheme: {detected_scheme}")
        except Exception as e:
            logger.error(f"Scheme detection failed: {e}")
            session.form_data["_active_schema"] = "General Agricultural Scheme"

        session.state = "APPLICATION_FORM"
        return f"Great, let's start your application for {session.form_data['_active_schema']}. First, what is your Aadhaar number?"
        
    # 2. Otherwise, fetch knowledge base context
    logger.info(f"[{session.session_id}] Fetching RAG context for query: {user_input}")
    context_chunks = retrieve_scheme_data(user_input)
    
    # 3. Build System Prompt with XML Context bounds and strict Personality Rules
    system_prompt = f"""You are Didi, a helpful and friendly AI assistant for the DidiGov government portal.
You speak clearly and concisely at a 6th-grade reading level.
You help farmers and citizens understand their eligibility for government schemes.

CRITICAL INSTRUCTIONS:
1. If the `<context>` block below contains information, answer the user's question ONLY using that specific information.
2. If the `<context>` block is empty or says "No specific scheme data found", you MAY use your general knowledge of Indian government agricultural schemes (like PM Kisan) to answer their question helpfully.
3. Keep your answer under 3 sentences unless explaining a complex list of documents.
4. YOU MUST ONLY ASK ONE QUESTION AT A TIME. Do not overwhelm the user with multiple follow-ups.
5. Gently guide the user towards starting an application form if they seem interested.

<context>
{context_chunks if context_chunks else "No specific scheme data found for this query."}
</context>
"""

    # 4. Invoke Nova Pro model with FULL conversation history
    logger.info(f"[{session.session_id}] Invoking Amazon Nova Pro LLM with Memory...")
    history_dicts = [m.dict() for m in session.messages]
    
    response_text = generate_response(
        system_prompt=system_prompt,
        messages=history_dicts
    )
    
    return response_text

def handle_application_form(session: ConversationSession, user_input: str) -> str:
    """
    State: APPLICATION_FORM
    We are actively extracting PII and structured data to fill out a JSON schema.
    """
    logger.info(f"[{session.session_id}] State: APPLICATION_FORM -> Processing input: {user_input}")
    
    import json
    
    # 1. Fetch the scheme context to get the required_user_fields array
    active_scheme = session.form_data.get("_active_schema", "PM Kisan")
    logger.info(f"[{session.session_id}] Fetching RAG schema context for: {active_scheme}")
    context_chunks = retrieve_scheme_data(f"What are the required_user_fields for {active_scheme}?")
    
    # 2. Build a highly strict extraction prompt
    system_prompt = f"""You are Didi, an AI JSON Data Extractor.
CRITICAL INSTRUCTIONS:
1. Review the conversation history and the <context> block below.
2. The <context> block contains a list of `required_user_fields` for the government scheme.
3. Determine which of these fields the user has already provided in the conversation.
4. The already extracted data is: {json.dumps(session.form_data, indent=2)}.
5. If the user provided new data or corrected existing data, UPDATE the values.
6. YOUR ENTIRE OUTPUT MUST BE A SINGLE, VALID JSON DICTIONARY.
7. CRITICAL: You MUST include ALL previously extracted fields in your output. Do not delete a field just because it wasn't mentioned in the current interaction!
8. CRITICAL: You MUST use the EXACT string keys extracted from the `required_user_fields` list in the <context> block. Do not invent human-readable keys.

<context>
{context_chunks if context_chunks else "[]"}
</context>
    """
    
    logger.info(f"[{session.session_id}] Invoking Amazon Nova Pro for Data Extraction...")
    
    # Do not pass the raw message list, otherwise the LLM thinks it's supposed to chat.
    # We serialize the history into a block of text to analyze.
    history_text = "\n".join([f"{m.role}: {m.content}" for m in session.messages])
    user_prompt = f"""Extract the requested fields from this history.
<history>
{history_text}
</history>
Output ONLY a raw JSON dictionary representing the fully updated `form_data`. 
CRITICAL RULES:
1. You MUST use the exact programmatic string keys provided in the <context> block (e.g., if the context says "full_name", do not output "Name").
2. You MUST include all fields from the existing data. Do NOT drop fields.
If no new data was found, output the existing data exactly as it was provided."""

    json_output = ""
    try:
        # We explicitly pass only ONE user message telling the LLM to execute the extraction.
        json_output = generate_response(
            system_prompt=system_prompt, 
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # Clean markdown formatting if the LLM hallucinated it
        if json_output.startswith("```json"):
            json_output = json_output[7:-3].strip()
        elif json_output.startswith("```"):
            json_output = json_output[3:-3].strip()
            
        extracted_data = json.loads(json_output)
        
        # Merge new data into the session form_data
        for key, value in extracted_data.items():
            if value and value.lower() not in ["", "none", "null", "unknown"]:
                session.form_data[key] = value
                
        logger.info(f"[{session.session_id}] Updated form data: {session.form_data}")
        
    except Exception as e:
        logger.error(f"Failed to parse LLM JSON extraction: {e} | Raw Output: {json_output}")
        # Continue anyway, we just might not have new data
        pass

    # 3. Determine the next question to ask
    # We'll do a quick secondary LLM call (or hardcode) to generate the question.
    # To save time and latency, we'll use a fast generation.
    question_prompt = f"""You are Didi, a helpful and friendly government assistant.
The user is filling out an application form for the {active_scheme} scheme.

Here are the required fields for this scheme:
<required_fields>
{context_chunks if context_chunks else "Name, Aadhaar, Mobile Number"}
</required_fields>

Here is the data we have collected so far:
<collected_data>
{json.dumps(session.form_data, indent=2)}
</collected_data>

Determine which required fields are still missing.
Ask the user ONE short, polite question to get the NEXT missing piece of information.
DO NOT ask for more than one thing at a time.
If ALL required fields from the list have been successfully collected, ask them to CONFIRM the application to submit it.
"""
    history_dicts = [m.dict() for m in session.messages]
    assistant_reply = generate_response(system_prompt=question_prompt, messages=history_dicts)
    
    if "confirm" in assistant_reply.lower() or "submit" in assistant_reply.lower():
        session.state = "APPLICATION_CONFIRMATION"
        
    return assistant_reply

def handle_application_confirmation(session: ConversationSession, user_input: str) -> str:
    """
    State: APPLICATION_CONFIRMATION
    User is verifying their payload before we execute the backend submission.
    """
    logger.info(f"[{session.session_id}] State: APPLICATION_CONFIRMATION -> Processing input: {user_input}")
    
    if "yes" in user_input.lower() or "correct" in user_input.lower() or "submit" in user_input.lower():
        session.state = "STATUS_CHECK"
        
        import uuid
        from datetime import datetime
        from models.session import DidiApplication
        from services.db_client import save_application
        
        app_id = f"APP-{str(uuid.uuid4())[:8].upper()}"
        now = datetime.utcnow().isoformat()
        scheme_id = session.form_data.get("_active_schema", "Unknown Scheme")
        
        application = DidiApplication(
            application_id=app_id,
            scheme_id=scheme_id,
            user_id=session.user_id,
            data=session.form_data,
            status="PENDING",
            created_at=now
        )
        
        try:
            save_application(application)
            return f"Perfect! Your application for {scheme_id} has been submitted successfully to the government portal. Your tracking number is {app_id}. You can ask me for status updates anytime."
        except Exception as e:
            logger.error(f"Failed to save application: {e}")
            return "I'm sorry, there was a system error while saving your application. Please try again later by saying 'Start application'."
    else:
        # Reset form
        session.form_data = {}
        session.state = "APPLICATION_FORM"
        return "Okay, let's start over. What is your Aadhaar number?"

def handle_status_check(session: ConversationSession, user_input: str) -> str:
    """
    State: STATUS_CHECK
    User is following up on a pending application.
    """
    logger.info(f"[{session.session_id}] State: STATUS_CHECK -> Processing input: {user_input}")
    
    # Fetch user's applications
    user_apps = get_user_applications(session.user_id)
    
    if not user_apps:
        session.state = "IDLE"
        return "I could not find any submitted applications linked to your mobile number. Would you like to start a new application?"
        
    # Sort and pick the most recent
    user_apps.sort(key=lambda x: x.get("created_at", ""), reverse=True)
    latest_app = user_apps[0]
    
    status = latest_app.get("status", "UNKNOWN")
    reason = latest_app.get("reason", "")
    scheme = latest_app.get("scheme_id", "a government scheme")
    
    # Build dynamic LLM response instructions
    system_prompt = f"""You are Didi, a helpful Indian government scheme assistant. 
The user is asking about the status of their application for '{scheme}'.

Here is the EXACT database status:
- Status: {status}
- Reason (if any): {reason}

Provide a polite, natural, 1-2 sentence response informing them of this status. Do NOT mention database keys or JSON, just speak naturally like a helpful officer."""

    response = generate_response(
        system_prompt=system_prompt,
        messages=[{"role": "user", "content": user_input}]
    )
    
    # Once checking status is done, go back to IDLE
    session.state = "IDLE"
    return response

# ── Main Endpoint ─────────────────────────────────────────────────────────────

@router.post("/message")
async def process_chat_message(
    payload: Dict[str, Any] = Body(...),
    session: ConversationSession = Depends(get_current_session)
):
    """
    Accepts text from the user (from the STT layer), passes it through the
    State Router, updates the DynamoDB Session History, and returns the response.
    """
    user_text = payload.get("message", "").strip()
    # The frontend will now pass its active language down to the chat endpoint
    # e.g. "te" for Telugu, "hi" for Hindi. Default to English.
    user_lang = payload.get("user_language", "en")
    
    if not user_text:
        raise HTTPException(status_code=400, detail="Missing parameter: 'message'")
        
    # 1. Append User Message (Always in English, thanks to Deepgram STT passing English down here)
    now = datetime.utcnow().isoformat()
    session.messages.append(ChatMessage(role="user", content=user_text, timestamp=now))
    
    # 2. State Machine Routing
    current_state = session.state.upper()
    
    if current_state == "IDLE":
        assistant_reply = handle_idle(session, user_text)
    elif current_state == "SCHEME_DISCUSSION":
        assistant_reply = handle_scheme_discussion(session, user_text)
    elif current_state == "APPLICATION_FORM":
        assistant_reply = handle_application_form(session, user_text)
    elif current_state == "APPLICATION_CONFIRMATION":
        assistant_reply = handle_application_confirmation(session, user_text)
    elif current_state == "STATUS_CHECK":
        assistant_reply = handle_status_check(session, user_text)
    else:
        logger.warning(f"Unknown state '{current_state}', resetting to IDLE.")
        session.state = "IDLE"
        assistant_reply = handle_idle(session, user_text)
        
    # 3. Append Assistant Response
    reply_time = datetime.utcnow().isoformat()
    session.messages.append(ChatMessage(role="assistant", content=assistant_reply, timestamp=reply_time))
    
    # 4. Flush to DynamoDB (Saving the English version so the ML Context window stays clean)
    update_session(
        session_id=session.session_id,
        state=session.state,
        messages=[m.dict() for m in session.messages],
        form_data=session.form_data
    )
    
    # 5. Phase 7: Translation & Text-To-Speech Generation
    # We must translate the English LLM output back into the user's spoken language
    final_text_to_speak = assistant_reply
    audio_b64 = ""
    
    if user_lang != "en":
        logger.info(f"[{session.session_id}] Translating response to {user_lang}")
        final_text_to_speak = translate_to_language(assistant_reply, target_lang=user_lang)

    # Convert the Final Text to an MP3
    logger.info(f"[{session.session_id}] Synthesizing Polly MP3 buffer...")
    # Map simple lang codes to Amazon Polly voice names
    # Using 'Aditi' as the universal Indian fallback because some older boto3
    # versions do not include Shruti/Kajal in their Enum validation constraints.
    polly_voice_map = {
        "hi": ("hi-IN", "Aditi"),
        "te": ("hi-IN", "Aditi"),
        "ta": ("hi-IN", "Aditi"), 
        "en": ("en-IN", "Aditi")
    }
    
    polly_args = polly_voice_map.get(user_lang, ("hi-IN", "Aditi"))
    audio_b64 = synthesize_speech(
        text=final_text_to_speak,
        language_code=polly_args[0],
        voice_id=polly_args[1],
        # Indian voices historically lack reliable neural engine support across regions
        engine="standard" 
    )
    
    return {
        "success": True,
        # Return the translated text to display on screen
        "reply": final_text_to_speak, 
        "new_state": session.state,
        "form_data": session.form_data,
        "audio_base64": audio_b64
    }
