import logging
import base64
from config import settings
from services.aws_clients import get_polly_client

logger = logging.getLogger("didi.polly")

def synthesize_speech(text: str, language_code: str = "hi-IN", voice_id: str = "Aditi", engine: str = "neural") -> str:
    """
    Synthesizes text into an MP3 audio buffer using Amazon Polly.
    Returns the binary payload encoded as a base64 string, so the React frontend
    can dynamically construct an AudioContext object.
    
    Defaults to Hindi (Aditi, Neural).
    """
    if not text.strip():
        return ""
        
    try:
        client = get_polly_client()
        
        response = client.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId=voice_id,
            LanguageCode=language_code,
            Engine=engine
        )
        
        if "AudioStream" in response:
            audio_bytes = response["AudioStream"].read()
            # Encode binary MP3 to base64 so it can be passed over JSON
            encoded_str = base64.b64encode(audio_bytes).decode("utf-8")
            return encoded_str
            
        logger.error("Polly response did not contain an AudioStream.")
        return ""
        
    except Exception as e:
        logger.error(f"Error calling AWS Polly: {str(e)}")
        return ""
