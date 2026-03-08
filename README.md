# 🇮🇳 DidiGov - AI for Bharat

*Multilingual Voice AI Assistant for Government Schemes*

DidiGov is a fully conversational, voice-first AI platform built to bridge the digital divide for Indian citizens. Powered by AWS Bedrock (Amazon Nova Pro) and Amazon Polly, Didi understands spoken regional languages, answers questions about government schemes using Retrieval-Augmented Generation (RAG), and dynamically guides users through voice-driven application forms. 

Users simply talk to "Didi", and she handles the complexity of data extraction and form submission directly to the government database.

## 🚀 Key Features
* **Multilingual Voice Interface:** Speak to Didi in English, Hindi, Telugu, or Tamil. She listens (via Groq Whisper STT) and speaks back natively (via Amazon Polly TTS).
* **Smart RAG Scheme Discovery:** Ask Didi about schemes like *PM Kisan* or *Ayushman Bharat*. She fetches accurate, real-time context from an AWS Knowledge Base to answer complex questions instantly.
* **Invisible Form Filling:** Say "I want to apply". Didi detects the scheme, dynamically fetches the required fields (Name, Aadhaar, Village), and guides you through a conversational voice interview to extract the information.
* **Intelligent Auto-Correction:** If you realize you misspoke ("Wait, my Aadhaar is actually 8888"), Didi automatically patches the extracted JSON payload.
* **Government Officer Portal:** A dedicated React Dashboard (`/admin`) for nodal officers to review extracted JSON application payloads and approve or reject submissions stored securely in DynamoDB.

---

## 🏗️ Architecture Stack
* **Frontend:** React + TypeScript + Vite. Uses standard HTML5 Web Audio components.
* **Backend:** FastAPI (Python). State-machine driven LLM routing.
* **Database:** AWS DynamoDB (`didi_users`, `didi_conversations`, `didi_applications`).
* **LLM / RAG:** Amazon Nova Pro via AWS Bedrock + Bedrock Knowledge Bases.
* **Speech-to-Text (STT):** Groq API (Whisper-Large-v3).
* **Text-to-Speech (TTS):** Amazon Polly (Aditi Voice).

---

## 🛠️ Local Setup Instructions

### Prerequisites
1. **Python 3.9+** installed locally.
2. **Node.js v18+** installed locally.
3. An active **AWS Account** with Bedrock, Polly, and DynamoDB permissions.
4. AWS CLI configured locally (`aws configure`).
5. A **Groq API Key** for real-time transcription.

### 1. Database Configuration
Ensure the following DynamoDB tables are created in your AWS Region (e.g., `ap-south-1`):
* `didi_users` (Partition Key: `mobile_number` [String])
* `didi_conversations` (Partition Key: `session_id` [String])
* `didi_applications` (Partition Key: `application_id` [String])

### 2. Backend Setup
Navigate into the `backend/` directory:
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

Create a `.env` file in the `backend/` directory with the following variables:
```env
# AWS Setup
AWS_REGION=ap-south-1
# Bedrock Foundation Model
BEDROCK_MODEL_ID=amazon.nova-pro-v1:0
# The ID of your AWS Bedrock Knowledge Base containing the Scheme JSON rules
BEDROCK_KNOWLEDGE_BASE_ID=YOUR_KB_ID
# Groq
GROQ_API_KEYS=your_groq_api_key_1,your_groq_api_key_2
# DynamoDB
DYNAMODB_USERS_TABLE=didi_users
DYNAMODB_CONVERSATIONS_TABLE=didi_conversations
DYNAMODB_APPLICATIONS_TABLE=didi_applications
```

Start the FastAPI server:
```bash
uvicorn main:app --reload --port 8000
```

### 3. Frontend Setup
Navigate into the `frontend/` directory:
```bash
cd frontend
npm install
```

Ensure `frontend/src/services/api.ts` points to `http://127.0.0.1:8000`.

Start the React development server:
```bash
npm run dev
```

---

## 💻 Usage & Portals

### Citizen Voice Assistant
1. Open `http://localhost:5173/` in Google Chrome.
2. Enter any 10-digit mobile number to login.
3. Click the microphone button and ask: *"Tell me about PM Kisan"* or *"I want to apply for building a concrete house."*
4. Chat naturally with Didi. Stop her by clicking the mic again if you want to interrupt. 
5. Complete the interview to submit your application.

### Nodal Officer Dashboard
1. Open `http://localhost:5173/admin` in your browser.
2. View the grid of live applications fetched straight from DynamoDB.
3. Click **Review** to open the details modal.
4. Inspect the clean JSON Extracted Payload.
5. Provide a typed reason and click **Approve** or **Reject** to dispatch the decision back to the database.
