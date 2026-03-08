from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from uuid import uuid4
import os
import time

from .config import mock_applications_db, S3_BUCKET_NAME
from .aws_client import synthesize_speech, transcribe_audio
from .services.bedrock_service import ask_didi_bedrock

app = FastAPI()

# ==========================
# CORS & FOLDER SETUP
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if not os.path.exists("static"):
    os.makedirs("static")
if not os.path.exists("temp_audio"):
    os.makedirs("temp_audio")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================
# HACKATHON MEMORY STORE
# ==========================
user_sessions = {}

# ==========================
# CITIZEN VOICE ENDPOINT
# ==========================
@app.post("/api/v1/process-voice")
async def process_voice(
    audio_file: UploadFile = File(...), 
    user_id: str = Form("9876543210"),
    language: str = Form("hi-IN")
):
    temp_path = f"temp_audio/{uuid4().hex}_{audio_file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await audio_file.read())
        
    print(f"\n--- NEW REQUEST ---")
    print(f"Processing audio from user: {user_id}")

    # 1. AWS Transcribe (Using Hackathon Bypass for now)
    try:
        raise Exception("Triggering Bypass until AWS is verified")
    except Exception as e:
        print("🚀 HACKATHON BYPASS ACTIVATED")
        # Simulating the final user confirmation
        citizen_question = "Yes, please submit my PM SVANidhi application. I have provided all details."
        print(f"Citizen asked (Simulated): {citizen_question}")

    # 2. AWS Bedrock: Get AI response AND Memory Session
    current_session_id = user_sessions.get(user_id)
    bedrock_result = ask_didi_bedrock(citizen_question, current_session_id)
    
    ai_data = bedrock_result["ai_data"]
    new_session_id = bedrock_result["session_id"]
    user_sessions[user_id] = new_session_id

    # Extract the specific JSON pieces
    speech_text = ai_data.get("speech_response", "I am processing your details.")
    extracted_info = ai_data.get("extracted_data", {})
    
    # PHASE 3: Grab the submission flag from Didi's brain
    is_ready_to_submit = ai_data.get("is_ready_to_submit", False)

    print(f"Didi says: {speech_text}")
    print(f"Extracted Data: {extracted_info}")
    print(f"Ready to Submit: {is_ready_to_submit}")

    # 3. Update Database Form Data
    if user_id not in mock_applications_db:
        mock_applications_db[user_id] = {
            "id": f"APP-{uuid4().hex[:6].upper()}",
            "user_id": user_id,
            "status": "In Progress",
            "timestamp": time.time(),
            "form_data": {}
        }
    
    # Dynamically merge whatever Bedrock extracted
    mock_applications_db[user_id]["form_data"].update(extracted_info)

    # PHASE 3: The Submission Trigger
    if is_ready_to_submit:
        mock_applications_db[user_id]["status"] = "Submitted"
        print(f"✅ Form officially submitted for {user_id}!")

    # 4. AWS Polly: Convert AI text to speech
    try:
        mp3_audio_bytes = synthesize_speech(speech_text)
        audio_filename = f"response_{user_id}_{uuid4().hex[:4]}.mp3"
        with open(f"static/{audio_filename}", "wb") as f:
            f.write(mp3_audio_bytes)
        audio_url = f"/static/{audio_filename}"
    except Exception as e:
        print(f"Polly Error: {e}")
        audio_url = None 

    if os.path.exists(temp_path):
        os.remove(temp_path)

    # 5. Return the payload
    return {
        "status": "success",
        "ai_response": speech_text,
        "audio_url": audio_url,
        "extracted_data": mock_applications_db[user_id]["form_data"],
        "application_status": mock_applications_db[user_id]["status"] # Send the status to the frontend
    }

# ==========================
# DUMMY GOV SANDBOX (Admin Routes)
# ==========================
@app.get("/api/v1/dummy-gov/applications")
def get_all_applications():
    apps = [{"id": k, **v} for k, v in mock_applications_db.items()]
    return {"applications": apps}

@app.put("/api/v1/dummy-gov/applications/{application_id}/approve")
def approve_application(application_id: str):
    for key, app_data in mock_applications_db.items():
        if app_data.get("id") == application_id or key == application_id:
            mock_applications_db[key]["status"] = "Approved"
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Application Not Found")

# NEW: The Reject route that accepts a reason
from pydantic import BaseModel

class RejectPayload(BaseModel):
    reason: str

@app.put("/api/v1/dummy-gov/applications/{application_id}/reject")
def reject_application(application_id: str, payload: RejectPayload):
    for key, app_data in mock_applications_db.items():
        if app_data.get("id") == application_id or key == application_id:
            mock_applications_db[key]["status"] = "Rejected"
            mock_applications_db[key]["rejection_reason"] = payload.reason
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Application Not Found")