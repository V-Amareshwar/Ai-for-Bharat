import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"
# A distinct fake mobile number to ensure a clean session table for this test
TEST_MOBILE = "7777777777" 

def print_step(title):
    print(f"\n{'='*60}\n▶ {title}\n{'='*60}")

def main():
    # 1. Login and get a fresh Session ID
    print_step("Phase 3: Login to generate new session bounds")
    login_req = requests.post(f"{BASE_URL}/auth/login", json={"mobile_number": TEST_MOBILE})
    if login_req.status_code != 200:
        print(f"Login failed: {login_req.text}")
        return
        
    session_id = login_req.json().get("session_id")
    print(f"✅ Logged in successfully. Session ID: {session_id}")
    
    headers = {
        "X-Session-Id": session_id,
        "Content-Type": "application/json"
    }

    # Helper function to send a message
    def send_msg(text):
        print(f"\n👤 You: {text}")
        start = time.time()
        res = requests.post(f"{BASE_URL}/chat/message", headers=headers, json={"message": text})
        duration = time.time() - start
        
        if res.status_code == 200:
            data = res.json()
            print(f"🤖 Didi: {data['reply']}")
            print(f"📊 New State: {data['new_state']}")
            print(f"⏱️  ({duration:.2f}s)")
            return data
        else:
            print(f"❌ Error: {res.status_code} - {res.text}")
            return None

    # ── Test Phase 6 (Conversational Memory) ──
    print_step("Prompt 1: Asking about a scheme (Initiates RAG Context)")
    send_msg("Tell me about crop insurance.")
    
    time.sleep(2)
    
    print_step("Prompt 2: Vague Follow-up (Relies entirely on DynamoDB memory)")
    # If Didi has memory, she will know "it" means the Crop Insurance scheme from Prompt 1.
    send_msg("Am I eligible for it?")

if __name__ == "__main__":
    main()
