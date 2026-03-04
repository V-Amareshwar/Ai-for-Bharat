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
# CORS
# ==========================
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Allows your localhost:3000 Next.js app to connect
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==========================
# FOLDER SETUP
# ==========================
# Ensure local folders exist for processing
if not os.path.exists("static"):
    os.makedirs("static")
if not os.path.exists("temp_audio"):
    os.makedirs("temp_audio")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================
# CITIZEN VOICE ENDPOINT
# ==========================
@app.post("/api/v1/process-voice")
async def process_voice(
    audio_file: UploadFile = File(...), 
    user_id: str = Form("9876543210"),
    language: str = Form("hi-IN")
):
    """
    1. Receives audio file from Frontend
    2. Transcribes it using AWS Transcribe
    3. Processes it with AWS Bedrock (Nova Pro)
    4. Converts response to speech via AWS Polly
    """
    # 1. Save the incoming audio file locally for processing
    temp_path = f"temp_audio/{uuid4().hex}_{audio_file.filename}"
    with open(temp_path, "wb") as buffer:
        buffer.write(await audio_file.read())
        
    print(f"Processing audio from user: {user_id}")

    try:
        # 2. AWS Transcribe: Turn voice into text
        citizen_question = transcribe_audio(temp_path, S3_BUCKET_NAME, language)
        print(f"Citizen asked: {citizen_question}")

        # 3. AWS Bedrock: Get AI response from Knowledge Base
        ai_text_response = ask_didi_bedrock(citizen_question)
        print(f"Didi's Answer: {ai_text_response}")

    except Exception as e:
        print(f"Workflow Error: {e}")
        # Fallback error message
        ai_text_response = "I'm sorry, I had trouble processing your request. Please try again."

    # 4. Update Mock Database (Simulating application start)
    mock_applications_db[user_id] = {
        "id": f"PM-{uuid4().hex[:6].upper()}",
        "user_id": user_id,
        "scheme": "Detected via AI",
        "status": "In Progress",
        "timestamp": time.time()
    }

    # 5. AWS Polly: Convert AI text to speech
    mp3_audio_bytes = synthesize_speech(ai_text_response)
    
    # Save the MP3 to the static folder for the frontend
    audio_filename = f"response_{user_id}_{uuid4().hex[:4]}.mp3"
    with open(f"static/{audio_filename}", "wb") as f:
        f.write(mp3_audio_bytes)
    
    # ==========================================
    # LIVE FORM DATA FOR THE FRONTEND
    # ==========================================
    # In a full version, Nova Pro would extract these entities
    current_extracted_data = {
        "Name": "User Detected",
        "Mobile Number": user_id,
        "Aadhaar Number": None,
        "Status": "Analyzing Speech..."
    }

    # Clean up the temporary uploaded file
    if os.path.exists(temp_path):
        os.remove(temp_path)

    # Return the final JSON payload
    return {
        "status": "success",
        "ai_response": ai_text_response,
        "audio_url": f"/static/{audio_filename}",
        "extracted_data": current_extracted_data
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