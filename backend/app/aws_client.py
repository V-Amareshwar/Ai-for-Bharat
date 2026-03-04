import boto3
import time
import uuid
import os
from .config import AWS_REGION

# Client Initializations
transcribe_client = boto3.client("transcribe", region_name=AWS_REGION)
polly_client = boto3.client("polly", region_name=AWS_REGION)
s3_client = boto3.client("s3", region_name=AWS_REGION)

def transcribe_audio(file_path: str, bucket_name: str, language_code: str = "hi-IN") -> str:
    job_name = f"transcription-{uuid.uuid4().hex}"
    s3_key = f"temp-audio/{os.path.basename(file_path)}"
    
    # 1. Upload to S3 (Transcribe requirement)
    s3_client.upload_file(file_path, bucket_name, s3_key)
    job_uri = f"s3://{bucket_name}/{s3_key}"

    # 2. Start AWS Transcribe Job
    transcribe_client.start_transcription_job(
        TranscriptionJobName=job_name,
        Media={'MediaFileUri': job_uri},
        MediaFormat='webm', # Matches your Next.js blob type
        LanguageCode=language_code
    )

    # 3. Poll for Completion (Max 30s)
    for _ in range(30):
        status = transcribe_client.get_transcription_job(TranscriptionJobName=job_name)
        if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
            break
        time.sleep(1)

    if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
        import requests
        transcript_url = status['TranscriptionJob']['Transcript']['TranscriptFileUri']
        transcript_text = requests.get(transcript_url).json()['results']['transcripts'][0]['transcript']
        
        # Cleanup
        transcribe_client.delete_transcription_job(TranscriptionJobName=job_name)
        return transcript_text
    
    raise Exception("Transcription failed or timed out.")

def synthesize_speech(text: str) -> bytes:
    response = polly_client.synthesize_speech(Text=text, OutputFormat="mp3", VoiceId="Aditi")
    return response["AudioStream"].read()