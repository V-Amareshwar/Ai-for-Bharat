import os
import boto3
from groq import Groq
from dotenv import load_dotenv
from .config import AWS_REGION

# Load the environment variables from the .env file
load_dotenv()

# ==========================================
# GROQ API KEY ROTATION (Comma-Separated)
# ==========================================
# 1. Fetch the single string from the .env file (defaults to empty string if missing)
keys_string = os.getenv("GROQ_API_KEYS", "")

# 2. Split the string by commas and clean up any accidental spaces
GROQ_API_KEYS = [key.strip() for key in keys_string.split(",") if key.strip()]

if not GROQ_API_KEYS:
    raise ValueError("CRITICAL ERROR: No Groq API keys found in the .env file! Please check your .env file.")

def transcribe_audio(audio_path: str, bucket_name: str = None, language: str = None) -> str:
    """
    Transcribes audio using Groq's Whisper API with automatic key rotation.
    (Bucket and language parameters are ignored, kept for compatibility with main.py)
    """
    last_error = None
    
    # Loop through the keys until one works
    for index, api_key in enumerate(GROQ_API_KEYS):
        try:
            client = Groq(api_key=api_key)
            
            with open(audio_path, "rb") as file:
                transcription = client.audio.transcriptions.create(
                    file=(os.path.basename(audio_path), file.read()),
                    model="whisper-large-v3"
                )
            
            print(f"✅ Transcription successful using Key #{index + 1}")
            return transcription.text

        except Exception as e:
            print(f"⚠️ Groq Key #{index + 1} Failed: {e}")
            last_error = e
            continue # If a key fails (rate limit/invalid), instantly try the next one

    # If the loop finishes and all keys are dead:
    print("❌ ALL GROQ KEYS FAILED.")
    raise Exception(f"Transcription failed. Last error: {last_error}")

# ==========================================
# AWS POLLY (Text-to-Speech)
# ==========================================
def synthesize_speech(text: str) -> bytes:
    """
    Converts Didi's text response into MP3 audio using AWS Polly.
    """
    client = boto3.client('polly', region_name=AWS_REGION)
    
    try:
        response = client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Kajal', # Hindi/Bilingual Indian voice
            Engine='neural'
        )
        return response['AudioStream'].read()
    except Exception as e:
        print(f"Polly Synthesis Error: {e}")
        raise e