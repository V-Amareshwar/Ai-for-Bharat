import requests

api_key = '6d02081437550db8a12fc1cbbdf0f041031a17ac'
DEEPGRAM_STT_URL = 'https://api.deepgram.com/v1/listen'

headers = {
    'Authorization': f'Token {api_key}',
    'Content-Type': 'audio/webm'
}

params = {
    'model': 'nova-3',
    'smart_format': 'true',
    'filler_words': 'false',
    'language': 'en'
}

print('Testing Deepgram Nova-3 EN natively...')
try:
    res = requests.post(DEEPGRAM_STT_URL, headers=headers, params=params, data=b'abcd'*100, timeout=10)
    print('Status:', res.status_code)
    print('Text:', res.text[:300])
except Exception as e:
    print('Deepgram Error:', e)
