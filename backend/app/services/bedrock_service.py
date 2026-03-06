"""
bedrock_service.py — Logic-first AI orchestration for Jan-Sahayak.

Auth state machine is enforced entirely in Python. The AI is used
only for two narrow tasks:
  1. Extract a phone number or name from free-form speech.
  2. Extract structured form fields from an authenticated conversation.

System prompts are kept minimal and used only where the AI genuinely
needs context about its role and output format.
"""

import boto3
import json
import re
import logging
from copy import deepcopy

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# Bedrock client (Nova Pro — first-party AWS)
# ──────────────────────────────────────────────
bedrock = boto3.client("bedrock-runtime", region_name="us-east-1")
MODEL_ID = "amazon.nova-pro-v1:0"
MAX_HISTORY = 10   # rolling window — last N user+assistant turns kept in memory

# ──────────────────────────────────────────────
# In-process session store (per device_id)
# Structure: { device_id: { "phone": str|None, "name": str|None, "history": [...] } }
# ──────────────────────────────────────────────
ACTIVE_SESSIONS: dict = {}

# ──────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────

def _digits_only(text: str) -> str:
    """Strip every non-digit character from a string."""
    return re.sub(r"\D", "", str(text))


def _extract_phone_from_text(text: str) -> str | None:
    """
    Pure-Python phone extraction — no AI needed.
    Handles localised number words → digits for common Indic patterns via
    regex.  Returns a 10-digit string or None.
    """
    # 1. Prefer an explicit 10-digit run already in the text
    candidates = re.findall(r"\b\d[\d\s\-]{8,}\d\b", text)
    for c in candidates:
        digits = _digits_only(c)
        if len(digits) >= 10:
            return digits[-10:]   # take last 10 in case ISD prefix present

    # 2. Check if the entire utterance, once cleaned, is ≥10 digits
    all_digits = _digits_only(text)
    if len(all_digits) >= 10:
        return all_digits[-10:]

    return None


def _extract_name_from_text(text: str) -> str | None:
    """
    Lightweight name extraction — only fires on unambiguous explicit patterns.
    Deliberately conservative: ambiguous short phrases fall through to the AI.
    """
    # Blacklist: common words that are NOT names
    _NON_NAMES = {
        "hello", "hi", "yes", "no", "okay", "ok", "thank", "thanks", "please",
        "sorry", "good", "fine", "haan", "nahi", "theek", "acha", "accha",
        "namaste", "helo", "hey", "sure", "done", "what", "how", "when",
    }

    # Only match EXPLICIT name-introduction patterns (not bare single words)
    patterns = [
        r"(?:my name is|i am called|mera naam hai|naam hai|mera naam)\s+([A-Za-z\u0900-\u097F]{2,30})",
        r"(?:main|mai)\s+([A-Za-z\u0900-\u097F]{2,30})\s+(?:hoon|hun|hu|hai|hain)",
        r"(?:i am|i'm)\s+([A-Za-z]{2,30})(?:\s|$)",
        # Single word ONLY if the whole utterance is just the name (no trailing words)
        r"^([A-Za-z\u0900-\u097F]{2,30})\s*[.!]?$",
    ]
    for pat in patterns:
        m = re.search(pat, text.strip(), re.IGNORECASE)
        if m:
            candidate = m.group(1).strip().capitalize()
            if candidate.lower() not in _NON_NAMES and len(candidate) >= 2:
                return candidate
    return None



def _call_bedrock(messages: list[dict], system_prompt: str, max_tokens: int = 500) -> dict:
    """
    Thin wrapper around Bedrock invoke_model using the Nova converse format.
    Returns the parsed JSON dict from the AI, or raises on failure.

    Robust JSON extraction:
    - Strips markdown fences
    - Scans for the first {...} block in the response (handles prose wrappers)
    - Raises ValueError if no valid JSON found
    """
    body = json.dumps({
        "system": [{"text": system_prompt}],
        "messages": messages,
        "inferenceConfig": {"maxTokens": max_tokens}
    })
    response = bedrock.invoke_model(modelId=MODEL_ID, body=body)
    raw = json.loads(response["body"].read())
    ai_text = raw["output"]["message"]["content"][0]["text"]

    # 1. Strip markdown fences
    cleaned = re.sub(r"```(?:json)?", "", ai_text).strip().strip("`")

    # 2. Try direct parse
    if cleaned:
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

    # 3. Scan for the first {...} block inside any surrounding prose
    #    This handles cases where the model says "Sure! Here is the JSON: {...}"
    match = re.search(r"(\{.*\})", cleaned, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass

    # 4. Nothing worked — model replied in prose instead of JSON.
    #    Rather than raising (which triggers the generic error fallback),
    #    we wrap the prose text directly as the speech_response.
    #    The user still HEARS Didi's answer via Polly; form data is just empty.
    logger.warning("Bedrock returned prose instead of JSON — wrapping as speech_response")
    prose = ai_text.strip()
    return {
        "speech_response": prose,
        "extracted_data": {},
        "is_ready_to_submit": False,
    }


def _build_bedrock_messages(history: list[dict]) -> list[dict]:
    """
    Convert our internal history (role: User/Didi) into Bedrock's
    [{"role": "user"/"assistant", "content": [{"text": "..."}]}] format.

    Bedrock strict rules enforced:
      1. First message MUST be role "user".
      2. Last message MUST be role "user".
      3. Roles must strictly alternate (no two consecutive same roles).
    """
    role_map = {"User": "user", "Didi": "assistant"}
    msgs = []

    for entry in history:
        role = role_map.get(entry["role"], "user")
        content = (entry.get("content") or "").strip()
        if not content:
            continue  # skip empty turns

        if msgs and msgs[-1]["role"] == role:
            # Merge consecutive same-role entries — bookkeeping artefact
            msgs[-1]["content"][0]["text"] += "\n" + content
        else:
            msgs.append({"role": role, "content": [{"text": content}]})

    # Rule 1: Strip any leading assistant messages — Bedrock must start with user
    while msgs and msgs[0]["role"] != "user":
        msgs.pop(0)

    # Rule 2: Strip any trailing non-user messages — final turn must be user
    while msgs and msgs[-1]["role"] != "user":
        msgs.pop()

    # Fallback: empty history
    return msgs or [{"role": "user", "content": [{"text": "Hello"}]}]


# ──────────────────────────────────────────────
# Main entry point
# ──────────────────────────────────────────────

def ask_didi_bedrock(user_input: str, device_id: str) -> dict:
    """
    Process one user turn for the given device session.

    Auth: phone number ONLY (no name required).
    Composite user ID = the 10-digit phone number itself.

    Returns:
        {
            "ai_data": {
                "speech_response": str,
                "extracted_data": dict,
                "is_ready_to_submit": bool
            },
            "composite_user_id": str | None   # e.g. "9010083154"
        }
    """
    # ── 1. Initialise session ──────────────────
    if device_id not in ACTIVE_SESSIONS:
        ACTIVE_SESSIONS[device_id] = {"phone": None, "history": []}

    session = ACTIVE_SESSIONS[device_id]
    session["history"].append({"role": "User", "content": user_input})

    # ── 2. Python phone-extraction gate ────────
    if not session["phone"]:
        # Try pure-Python first — fast, zero latency, zero cost
        phone = _extract_phone_from_text(user_input)

        if not phone:
            # Fallback: ask Bedrock only to extract the phone number
            try:
                bedrock_msgs = _build_bedrock_messages(session["history"][-MAX_HISTORY:])
                result = _call_bedrock(
                    messages=bedrock_msgs,
                    system_prompt=(
                        "You are a helpful Indian government assistant named Didi. "
                        "Your only task right now is to extract a 10-digit Indian mobile phone number "
                        "from the user's message. "
                        'Return ONLY raw JSON: {"extracted_phone": "XXXXXXXXXX"} '
                        "or null if no number is present. No explanation, no markdown."
                    ),
                    max_tokens=80,
                )
                ai_phone = result.get("extracted_phone")
                if ai_phone:
                    digits = _digits_only(str(ai_phone))
                    if len(digits) >= 10:
                        phone = digits[-10:]
            except Exception as exc:
                logger.warning("Bedrock phone extraction failed: %s", exc)

        if phone:
            session["phone"] = phone
            logger.info("[%s] Phone captured: %s", device_id, phone)
            speech = (
                f"Mobile number noted — ending in {phone[-4:]}. "
                "Which government scheme would you like to apply for? "
                "I can help with PM-Kisan, Ayushman Bharat, Pradhan Mantri Awas, and more. "
                "Please share your details and I'll fill the form for you."
            )
        else:
            speech = (
                "Welcome to Jan-Sahayak. "
                "To get started, please tell me your 10-digit mobile number."
            )

        didi_reply = {"speech_response": speech, "extracted_data": {}, "is_ready_to_submit": False}
        session["history"].append({"role": "Didi", "content": speech})
        return {"ai_data": didi_reply, "composite_user_id": session["phone"]}
    # ── 3. Authenticated — form filling ────────
    composite_id = session["phone"]  # just the phone number
    recent_history = session["history"][-MAX_HISTORY:]
    bedrock_msgs = _build_bedrock_messages(recent_history)

    # Minimal system prompt: only tell the AI its structured output contract
    # Python handles all auth, state enforcement, and data merging.
    system_prompt = (
        "You are Didi, a friendly multilingual Indian government assistant helping citizens "
        "fill out government scheme applications.\n"
        "Rules you MUST follow:\n"
        "1. ALWAYS respond in valid JSON — no exceptions, no plain text, no markdown.\n"
        "2. If the user asks a general question (e.g. 'What is PM-Kisan?'), answer it "
        "   conversationally inside the 'speech_response' field of the JSON.\n"
        "3. Only put data in 'extracted_data' when the user explicitly provides a value "
        "   (name, aadhaar, income, address, scheme name, land size, crop, bank account, etc.).\n"
        "4. If the user corrects a value ('no wait, income is 50000'), output the NEW value.\n"
        "5. Speak in the user's language (Hindi, Telugu, English, or mixed Hinglish).\n"
        "6. Set is_ready_to_submit=true ONLY when the user explicitly says to submit.\n\n"
        "OUTPUT FORMAT — MUST be raw JSON, nothing else:\n"
        '{"speech_response": "...", "extracted_data": {"field": "value"}, "is_ready_to_submit": false}'
    )

    try:
        ai_data = _call_bedrock(messages=bedrock_msgs, system_prompt=system_prompt, max_tokens=600)

        # Enforce types — extracted_data must be a dict
        if not isinstance(ai_data.get("extracted_data"), dict):
            ai_data["extracted_data"] = {}
        if not isinstance(ai_data.get("is_ready_to_submit"), bool):
            ai_data["is_ready_to_submit"] = False

        speech = ai_data.get("speech_response", "")
        session["history"].append({"role": "Didi", "content": speech})
        logger.info("[%s] Extracted: %s", composite_id, ai_data.get("extracted_data"))

        return {"ai_data": ai_data, "composite_user_id": composite_id}

    except Exception as exc:
        logger.error("[%s] Bedrock form-fill error: %s", composite_id, exc)
        fallback_speech = "मुझे एक समस्या आई। क्या आप फिर से बोल सकते हैं? (I hit an issue — please repeat.)"
        session["history"].append({"role": "Didi", "content": fallback_speech})
        return {
            "ai_data": {
                "speech_response": fallback_speech,
                "extracted_data": {},
                "is_ready_to_submit": False,
            },
            "composite_user_id": composite_id,
        }