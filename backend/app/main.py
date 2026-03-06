"""
main.py — FastAPI application entry point for Jan-Sahayak.

Key responsibilities:
  • Receive citizen voice uploads, transcribe, run through Didi AI, return response.
  • Persist every data update immediately to database.json via database.py.
  • Expose admin sandbox endpoints for reviewing/approving/rejecting applications.
"""

from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from uuid import uuid4
import os
import time
import logging

from .config import S3_BUCKET_NAME
from .aws_client import synthesize_speech, transcribe_audio
from .services.bedrock_service import ask_didi_bedrock
from .database import load_db, save_db, get_db

# ──────────────────────────────────────────────
# Logging
# ──────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────
# App bootstrap
# ──────────────────────────────────────────────
app = FastAPI(title="Jan-Sahayak API", version="1.0.0")

# Load persistent DB on startup
@app.on_event("startup")
def startup_event():
    load_db()
    logger.info("Database loaded. Records: %d", len(get_db()))

# ──────────────────────────────────────────────
# CORS
# ──────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ──────────────────────────────────────────────
# Static file folders
# ──────────────────────────────────────────────
for folder in ("static", "temp_audio"):
    os.makedirs(folder, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")



# ══════════════════════════════════════════════
# GREETING ENDPOINT (called on page load)
# ══════════════════════════════════════════════
GREET_TEXT = (
    "Jan-Sahayak mein aapka swagat hai. "
    "Shuruaat karne ke liye, kripya apna 10 angkon ka mobile number batayein."
)

@app.get("/api/v1/greet")
def greet():
    """
    Returns Didi's welcome audio. Called once when the frontend loads.
    No auth required — this is purely a TTS call to play the opening prompt.
    """
    try:
        mp3_bytes = synthesize_speech(GREET_TEXT)
        filename = f"greet_{uuid4().hex[:8]}.mp3"
        with open(f"static/{filename}", "wb") as f:
            f.write(mp3_bytes)
        return {"speech": GREET_TEXT, "audio_url": f"/static/{filename}"}
    except Exception as exc:
        logger.error("Greet TTS error: %s", exc)
        return {"speech": GREET_TEXT, "audio_url": None}


# ══════════════════════════════════════════════
# CITIZEN VOICE ENDPOINT
# ══════════════════════════════════════════════
@app.post("/api/v1/process-voice")
async def process_voice(
    audio_file: UploadFile = File(...),
    user_id: str = Form(...),          # Browser session/device fingerprint (not the real user ID)
    language: str = Form("hi-IN"),
):
    """
    Full pipeline:
      audio → Groq Whisper → Bedrock Didi → Polly TTS → JSON response
    """
    temp_path = f"temp_audio/{uuid4().hex}_{audio_file.filename}"
    try:
        # ── 1. Save upload ──────────────────────
        with open(temp_path, "wb") as buf:
            buf.write(await audio_file.read())

        # ── 2. Transcribe ───────────────────────
        try:
            citizen_text = transcribe_audio(temp_path)
            logger.info("Transcription: %r", citizen_text)
            if not citizen_text or len(citizen_text.strip()) < 2:
                raise ValueError("Empty transcription")
        except Exception as exc:
            logger.warning("Transcription failed: %s", exc)
            return _error_response("मुझे ठीक से सुनाई नहीं दिया। कृपया फिर से बोलें।")

        # ── 3. Didi AI (state machine + Bedrock) ─
        device_id = user_id.strip()
        bedrock_result = ask_didi_bedrock(citizen_text, device_id)

        ai_data          = bedrock_result["ai_data"]
        composite_id     = bedrock_result["composite_user_id"]
        speech_text      = ai_data.get("speech_response", "")
        extracted_info   = ai_data.get("extracted_data", {})
        is_ready         = ai_data.get("is_ready_to_submit", False)

        logger.info("Composite ID: %s | Extracted: %s", composite_id, extracted_info)

        # ── 4. Persist to database ──────────────
        db = get_db()
        active_form_data = {}
        application_status = "Authenticating..."

        if composite_id:
            if composite_id not in db:
                db[composite_id] = {
                    "id": f"APP-{uuid4().hex[:6].upper()}",
                    "user_id": composite_id,
                    "status": "In Progress",
                    "created_at": time.time(),
                    "updated_at": time.time(),
                    "form_data": {},
                }

            record = db[composite_id]

            if extracted_info:
                # .update() naturally OVERWRITES — this is Phase 4's correction fix
                record["form_data"].update(extracted_info)
                record["updated_at"] = time.time()

            if is_ready:
                record["status"] = "Submitted"
                logger.info("✅ Form submitted for %s", composite_id)

            # Persist to disk immediately after every mutation
            save_db()

            active_form_data   = record["form_data"]
            application_status = record["status"]

        # ── 5. Text-to-Speech ───────────────────
        audio_url = None
        try:
            mp3_bytes      = synthesize_speech(speech_text)
            audio_filename = f"response_{uuid4().hex[:8]}.mp3"
            with open(f"static/{audio_filename}", "wb") as f:
                f.write(mp3_bytes)
            audio_url = f"/static/{audio_filename}"
        except Exception as exc:
            logger.error("Polly TTS error: %s", exc)

        return {
            "status": "success",
            "ai_response": speech_text,
            "audio_url": audio_url,
            "extracted_data": active_form_data,
            "application_status": application_status,
        }

    finally:
        # Always clean up temp file
        if os.path.exists(temp_path):
            os.remove(temp_path)


def _error_response(message: str) -> dict:
    return {
        "status": "error",
        "ai_response": message,
        "audio_url": None,
        "extracted_data": {},
        "application_status": "Error",
    }


# ══════════════════════════════════════════════
# ADMIN SANDBOX ENDPOINTS
# ══════════════════════════════════════════════

@app.get("/api/v1/dummy-gov/applications")
def get_all_applications():
    db = get_db()
    return {"applications": list(db.values())}


@app.put("/api/v1/dummy-gov/applications/{application_id}/approve")
def approve_application(application_id: str):
    db = get_db()
    record = _find_record(db, application_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    record["status"] = "Approved"
    save_db()
    return {"status": "success"}


class RejectPayload(BaseModel):
    reason: str


@app.put("/api/v1/dummy-gov/applications/{application_id}/reject")
def reject_application(application_id: str, payload: RejectPayload):
    db = get_db()
    record = _find_record(db, application_id)
    if not record:
        raise HTTPException(status_code=404, detail="Application not found")
    record["status"] = "Rejected"
    record["rejection_reason"] = payload.reason
    save_db()
    return {"status": "success"}


def _find_record(db: dict, application_id: str) -> dict | None:
    """Look up by composite key OR by the APP-XXXXXX id field."""
    if application_id in db:
        return db[application_id]
    for record in db.values():
        if record.get("id") == application_id:
            return record
    return None