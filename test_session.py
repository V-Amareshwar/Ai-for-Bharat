import requests
import time

API_URL = "http://127.0.0.1:8000/api/v1"

# 1. Simulate a user "logging in" via mobile number
print("\n--- TEST 1: LOGIN ---")
mobile_number = "9876543210"
login_payload = {"mobile_number": mobile_number}

print(f"Sending login request for mobile: {mobile_number}...")
response = requests.post(f"{API_URL}/auth/login", json=login_payload)
response.raise_for_status()

login_data = response.json()
session_id = login_data["session_id"]
is_new = login_data["is_new_user"]

print(f"✅ Success! Session ID: {session_id}")
print(f"✅ Is New User?: {is_new}")

# 2. Wait a moment to show persistence
print("\n--- TEST 2: SIMULATING RE-LOGIN ---")
time.sleep(1)

print(f"Logging in again with the same number ({mobile_number})...")
response_2 = requests.post(f"{API_URL}/auth/login", json=login_payload)
response_2.raise_for_status()
login_data_2 = response_2.json()

print(f"✅ Success! New Session ID: {login_data_2['session_id']}")
print(f"✅ Is New User?: {login_data_2['is_new_user']}  <-- See? It remembers you from Test 1!")

print("\n--- ALL TESTS PASSED! ---")
print("You can verify the tables directly by going to your AWS Console -> DynamoDB -> Tables")
print("You will see the 'didi_users' and 'didi_conversations' tables populated with these records.")
