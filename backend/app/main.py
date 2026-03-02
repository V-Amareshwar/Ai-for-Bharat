from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from uuid import uuid4
import time

from .config import mock_applications_db
from .schemas import VoiceRequest
from .aws_client import synthesize_speech

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
# CITIZEN VOICE ENDPOINT (Fixed to match Frontend)
# ==========================
@app.post("/api/v1/process-voice")
async def process_voice(request: VoiceRequest):
    """
    Expects JSON: {"mobile_number": "9876543210"}
    (Note: ensure your schemas.py VoiceRequest has 'user_id' if your frontend sends 'user_id')
    """
    # For this hackathon demo, we extract the user ID (mobile number) sent by the frontend
    user_id = getattr(request, 'user_id', getattr(request, 'mobile_number', '9876543210'))

    # Simulated Bedrock AI text response
    ai_text_response = "दीदी यहाँ है। मैंने आपका पीएम स्वनिधि फॉर्म भर दिया है। इसे मंज़ूरी के लिए भेज दिया गया है।"

    # Update Mock Database
    mock_applications_db[user_id] = {
        "id": f"PM-{uuid4().hex[:6].upper()}",
        "user_id": user_id,
        "scheme": "PM SVANidhi",
        "status": "Pending Review",
        "timestamp": time.time()
    }

    # Synthesize audio bytes using Polly
    mp3_audio_bytes = synthesize_speech(ai_text_response)
    
    # Save the bytes to a local file so the frontend can play it via a URL
    audio_filename = f"response_{user_id}.mp3"
    with open(audio_filename, "wb") as f:
        f.write(mp3_audio_bytes)
    
    # ==========================================
    # NEW: LIVE FORM DATA FOR THE FRONTEND
    # ==========================================
    current_extracted_data = {
        "Name": "रामू (Ramu)",
        "Mobile Number": user_id,
        "Aadhaar Number": None, # None means the AI hasn't collected it yet
        "Pincode": None,
        "Ration Card": None
    }

    # Return the exact JSON structure your Next.js app expects!
    return {
        "status": "success",
        "ai_response": ai_text_response,
        "audio_url": f"/static/{audio_filename}",
        "extracted_data": current_extracted_data
    }

# ==========================
# STATIC FILES (To serve the MP3 to the frontend)
# ==========================
from fastapi.staticfiles import StaticFiles
import os

# Create static folder if it doesn't exist
if not os.path.exists("static"):
    os.makedirs("static")

app.mount("/static", StaticFiles(directory="static"), name="static")

# ==========================
# DUMMY GOV SANDBOX (Admin Routes)
# ==========================
@app.get("/api/v1/dummy-gov/applications")
def get_all_applications():
    # Convert dict to list for the frontend admin table
    apps = [{"id": k, **v} for k, v in mock_applications_db.items()]
    return {"applications": apps}

@app.put("/api/v1/dummy-gov/applications/{application_id}/approve")
def approve_application(application_id: str):
    # Find and approve
    for key, app_data in mock_applications_db.items():
        if app_data.get("id") == application_id or key == application_id:
            mock_applications_db[key]["status"] = "Approved"
            return {"status": "success"}
    raise HTTPException(status_code=404, detail="Application Not Found")