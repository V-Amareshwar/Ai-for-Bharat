import requests
import json
import time

BASE_URL = "http://127.0.0.1:8000/api/v1"
TEST_MOBILE = "1111111111" # Distinct fake user

def print_step(title):
    print(f"\n{'='*50}\n▶ {title}\n{'='*50}")

def main():
    # 1. Login and get a fresh Session ID
    print_step("Phase 3: Login to generate new session")
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
            print(f"📝 Form Data: {data['form_data']}")
            print(f"⏱️  ({duration:.2f}s)")
            return data
        else:
            print(f"❌ Error: {res.status_code} - {res.text}")
            return None

    # ── Test the 4-Step State Machine Matrix ──

    print_step("Phase 4 Flow: IDLE -> SCHEME_DISCUSSION")
    send_msg("I want crop insurance") # Should trigger transition

    print_step("Phase 4 Flow: SCHEME_DISCUSSION -> APPLICATION_FORM")
    send_msg("Okay, let's start the application form")

    print_step("Phase 4 Flow: Populate Aadhaar Slot")
    send_msg("888899991111")

    print_step("Phase 4 Flow: Populate Land Slot -> CONFIRMATION")
    send_msg("2.5 hectares")

    print_step("Phase 4 Flow: APPLICATION_CONFIRMATION -> STATUS_CHECK")
    send_msg("Yes, that is correct!")

if __name__ == "__main__":
    main()
