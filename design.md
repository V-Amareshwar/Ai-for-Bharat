# Design Document — Jan-Sahayak

> **Voice-First, Text-Free PWA for Illiterate Indian Citizens to Access Government Schemes via Actionable AI Agents**

---

## Table of Contents

1. [System Architecture (HLD)](#1-system-architecture-hld)
2. [Voice-to-Action Pipeline (Detailed Data Flow)](#2-voice-to-action-pipeline-detailed-data-flow)
3. [Database Schema (DynamoDB)](#3-database-schema-dynamodb)
4. [API Design (FastAPI Interface)](#4-api-design-fastapi-interface)
5. [Security & Optimization](#5-security--optimization)

---

## 1. System Architecture (HLD)

### 1.1 High-Level Overview

Jan-Sahayak follows a **fully serverless, event-driven architecture** composed of four decoupled layers. Every component is managed by AWS, ensuring near-zero idle cost and infinite horizontal scalability.

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FRONTEND LAYER                               │
│          Next.js 14 PWA  (Vercel / AWS Amplify Hosting)             │
│   ┌──────────┐  ┌──────────────┐  ┌──────────────────────────┐     │
│   │ Service  │  │ MediaRecorder│  │  Cartoon-Based UI        │     │
│   │ Worker   │  │ (Audio Blob) │  │  (Tailwind + Framer)     │     │
│   └──────────┘  └──────┬───────┘  └──────────────────────────┘     │
└─────────────────────────┼───────────────────────────────────────────┘
                          │ HTTPS (REST / Streaming)
┌─────────────────────────▼───────────────────────────────────────────┐
│                        API LAYER                                    │
│              Amazon API Gateway (HTTP API v2)                       │
│           ┌──────────────────────────────────┐                      │
│           │  AWS Lambda (Python 3.12)        │                      │
│           │  FastAPI + Mangum Adapter        │                      │
│           │  ──────────────────────────      │                      │
│           │  /process-voice                  │                      │
│           │  /schemes/recommended            │                      │
│           │  /application/submit             │                      │
│           └──────────────┬───────────────────┘                      │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
          ┌────────────────┼─────────────────────┐
          ▼                ▼                     ▼
┌──────────────┐  ┌────────────────┐  ┌────────────────────────────┐
│  DATA LAYER  │  │   AI LAYER     │  │   VOICE LAYER              │
│              │  │  ("The Brain") │  │                            │
│  DynamoDB    │  │  Bedrock Agent │  │  Amazon Transcribe (STT)   │
│  (Users,     │  │  (Claude 3     │  │  Amazon Translate          │
│   Schemes,   │  │   Sonnet)      │  │  Amazon Polly (TTS)        │
│   Apps)      │  │                │  │                            │
│              │  │  Bedrock       │  └────────────────────────────┘
│  S3          │  │  Knowledge     │
│  (PDFs,      │  │  Base (RAG     │
│   Audio)     │  │   over Govt    │
│              │  │   PDFs)        │
└──────────────┘  └────────────────┘
```

### 1.2 Layer Breakdown

#### A. Frontend Layer — Next.js 14 PWA

| Aspect | Detail |
|---|---|
| **Framework** | Next.js 14 (App Router) with TypeScript |
| **Hosting** | Vercel (free tier) or AWS Amplify Hosting |
| **Styling** | Tailwind CSS (mobile-first, large touch targets) |
| **PWA** | `next-pwa` plugin; Service Worker caches static assets (cartoons, icons, pre-recorded audio prompts) |
| **Audio Capture** | Browser-native `MediaRecorder` API → outputs `audio/webm` blob |
| **Audio Playback** | `HTMLAudioElement` consuming chunked audio stream from Polly |
| **Offline** | Cached cartoon avatars + pre-recorded fallback prompts in Telugu/Hindi |

**Key Design Decision:** The UI is **entirely icon/cartoon-driven**. No text labels are rendered. Each persona (Farmer, Student, Worker, Senior Citizen) is represented by a semi-abstracted illustration that plays its name audio on hover/tap.

#### B. API Layer — API Gateway + Lambda

| Aspect | Detail |
|---|---|
| **Gateway** | Amazon API Gateway HTTP API (v2) — lower latency, lower cost than REST API |
| **Compute** | AWS Lambda (Python 3.12, ARM64/Graviton2 for cost savings) |
| **Framework** | FastAPI wrapped with the **Mangum** adapter for Lambda compatibility |
| **Cold Start Mitigation** | Provisioned concurrency = 1 (free tier allows 1); Lambda SnapStart evaluated |
| **Timeout** | 29 seconds (API Gateway max); target response < 3 seconds |
| **Memory** | 512 MB (balances cost vs. performance for AI SDK calls) |

**Key Design Decision:** A single Lambda function hosts all FastAPI routes (monolithic Lambda). This avoids per-route cold starts and keeps the deployment simple for a hackathon prototype.

#### C. Data Layer — DynamoDB + S3

| Service | Purpose |
|---|---|
| **DynamoDB** | Stores user profiles, scheme metadata, and application records (see Section 3) |
| **S3 — `jansahayak-docs` bucket** | Stores Government Scheme PDFs (ingested into Bedrock Knowledge Base) |
| **S3 — `jansahayak-audio` bucket** | Temporary storage for user audio blobs (auto-deleted via S3 Lifecycle Rule after 24h) |

#### D. AI Layer — "The Brain"

| Component | Role |
|---|---|
| **Amazon Bedrock — Claude 3 Sonnet** | Primary LLM for intent classification, entity extraction, conversational response generation |
| **Amazon Bedrock Knowledge Base** | Managed RAG pipeline: ingests PDFs from S3, chunks them, creates embeddings (Titan Embeddings v2), stores vectors in OpenSearch Serverless, retrieves relevant passages at query time |
| **Bedrock Agent** | Orchestrates multi-step tool use: (1) Query Knowledge Base, (2) Extract form entities, (3) Generate user-facing response — all in a single invocation |

**Key Design Decision:** We use **Bedrock Knowledge Bases** (managed RAG) instead of self-hosted vector databases. This eliminates infrastructure overhead and guarantees zero-hallucination by restricting the LLM's context to only the retrieved PDF chunks.

---

## 2. Voice-to-Action Pipeline (Detailed Data Flow)

This is the core innovation of Jan-Sahayak — converting a spoken query in a regional language into an actionable government scheme application, entirely hands-free.

### 2.1 End-to-End Sequence Diagram

```
 User (Telugu)       Frontend (PWA)        API Gateway       Lambda (FastAPI)
 ─────────────       ──────────────        ───────────       ────────────────
      │                    │                    │                    │
      │  🎤 Speaks         │                    │                    │
      │  "నాకు రైతు        │                    │                    │
      │   బంధు కావాలి"     │                    │                    │
      │───────────────────>│                    │                    │
      │                    │                    │                    │
      │            MediaRecorder               │                    │
      │            captures blob               │                    │
      │            (audio/webm)                │                    │
      │                    │                    │                    │
      │                    │  PUT audio blob    │                    │
      │                    │  to S3 (presigned) │                    │
      │                    │───────────────────>│                    │
      │                    │                    │                    │
      │                    │  POST /process-voice                   │
      │                    │  { s3_key, lang }  │                    │
      │                    │───────────────────>│───────────────────>│
      │                    │                    │                    │
      │                    │                    │         ┌──────────┴──────────┐
      │                    │                    │         │  STEP 1: Transcribe │
      │                    │                    │         │  S3 → Amazon        │
      │                    │                    │         │  Transcribe         │
      │                    │                    │         │  (Telugu ASR)       │
      │                    │                    │         │  → Telugu Text      │
      │                    │                    │         ├─────────────────────┤
      │                    │                    │         │  STEP 2: Translate  │
      │                    │                    │         │  Telugu Text →      │
      │                    │                    │         │  Amazon Translate   │
      │                    │                    │         │  → English Text     │
      │                    │                    │         ├─────────────────────┤
      │                    │                    │         │  STEP 3: RAG Query  │
      │                    │                    │         │  English Text →     │
      │                    │                    │         │  Bedrock Knowledge  │
      │                    │                    │         │  Base → Scheme      │
      │                    │                    │         │  Rules Retrieved    │
      │                    │                    │         ├─────────────────────┤
      │                    │                    │         │  STEP 4: Agent      │
      │                    │                    │         │  Context + Rules →  │
      │                    │                    │         │  Bedrock Agent      │
      │                    │                    │         │  (Claude 3 Sonnet)  │
      │                    │                    │         │  → Intent + Entities│
      │                    │                    │         │  → Response Text    │
      │                    │                    │         ├─────────────────────┤
      │                    │                    │         │  STEP 5: Translate  │
      │                    │                    │         │  Response (EN) →    │
      │                    │                    │         │  Amazon Translate   │
      │                    │                    │         │  → Telugu Text      │
      │                    │                    │         ├─────────────────────┤
      │                    │                    │         │  STEP 6: Polly TTS  │
      │                    │                    │         │  Telugu Text →      │
      │                    │                    │         │  Amazon Polly       │
      │                    │                    │         │  → Audio Stream     │
      │                    │                    │         └──────────┬──────────┘
      │                    │                    │                    │
      │                    │  Response: {       │                    │
      │                    │    audio_url,      │<───────────────────│
      │                    │    extracted_entities,                  │
      │                    │    scheme_info,     │                    │
      │                    │    next_question    │                    │
      │                    │  }                 │                    │
      │                    │<───────────────────│                    │
      │                    │                    │                    │
      │  🔊 Plays Audio    │                    │                    │
      │  "రైతు బంధు లో...  │                    │                    │
      │   మీ పేరు చెప్పండి"│                    │                    │
      │<───────────────────│                    │                    │
```

### 2.2 Step-by-Step Breakdown

#### Step 1 — Audio Capture (Frontend)

```
User taps 🎤 → MediaRecorder starts (audio/webm; codecs=opus)
User speaks → MediaRecorder.ondataavailable collects chunks
User taps ⏹ → Blob assembled → Uploaded to S3 via presigned PUT URL
```

- **Why presigned URL?** Avoids sending large binary payloads through API Gateway (which has a 10 MB limit and charges per GB). Direct S3 upload is free and fast.
- **S3 Key Format:** `audio/{user_id}/{timestamp}.webm`

#### Step 2 — Speech-to-Text (Amazon Transcribe)

```python
# Lambda handler pseudocode
transcribe_client.start_transcription_job(
    TranscriptionJobName=job_id,
    LanguageCode="te-IN",          # Telugu (India)
    Media={"MediaFileUri": s3_uri},
    OutputBucketName="jansahayak-audio",
    Settings={"ShowSpeakerLabels": False}
)
```

- **Supported Languages:** `te-IN` (Telugu), `hi-IN` (Hindi)
- **Latency Optimization:** Use `start_stream_transcription` (streaming API) for real-time partial results instead of batch jobs (reduces wait from ~5s to ~1.5s)
- **Output:** Raw transcribed text in the user's language

#### Step 3 — Translation (Amazon Translate)

```python
# Only triggered if source language ≠ English
translated = translate_client.translate_text(
    Text=telugu_text,
    SourceLanguageCode="te",
    TargetLanguageCode="en"
)
english_query = translated["TranslatedText"]
```

- **Why translate?** Claude 3 Sonnet performs best with English prompts. The Knowledge Base embeddings are also in English (Government PDFs are officially in English).
- **Bypass:** If the user speaks in English (detected via Transcribe), skip this step.

#### Step 4 — RAG Retrieval (Bedrock Knowledge Base)

```python
response = bedrock_agent_runtime.retrieve(
    knowledgeBaseId="KB_GOVT_SCHEMES",
    retrievalQuery={"text": english_query},
    retrievalConfiguration={
        "vectorSearchConfiguration": {
            "numberOfResults": 5    # Top 5 relevant chunks
        }
    }
)
scheme_context = "\n".join([r["content"]["text"] for r in response["retrievalResults"]])
```

- **Data Source:** Government scheme PDFs (Rythu Bandhu GO, Aasara Pension Guidelines, PM-KISAN rules) uploaded to S3 and ingested into the Knowledge Base.
- **Embedding Model:** Amazon Titan Embeddings v2
- **Vector Store:** Amazon OpenSearch Serverless (managed by Bedrock)
- **Chunking Strategy:** Fixed-size (300 tokens) with 10% overlap

#### Step 5 — Agent Reasoning & Entity Extraction (Bedrock Agent / Claude 3 Sonnet)

```python
prompt = f"""
You are Jan-Sahayak, a helpful government schemes assistant for Indian citizens.

CONTEXT (from official government documents):
{scheme_context}

USER QUERY: {english_query}

CONVERSATION HISTORY: {session_history}

INSTRUCTIONS:
1. Answer the user's question ONLY using the CONTEXT above.
2. If the user provides personal details, extract them into a JSON:
   {{"name": "...", "age": ..., "income": ..., "land_acres": ..., "caste": "..."}}
3. If you need more details to fill the form, ask the NEXT question.
4. If the CONTEXT does not contain the answer, say "I do not have information about this."

Respond in this JSON format:
{{
  "response_text": "...",
  "extracted_entities": {{}},
  "form_complete": false,
  "next_question": "What is your annual income?"
}}
"""

bedrock_response = bedrock_runtime.invoke_model(
    modelId="anthropic.claude-3-sonnet-20240229-v1:0",
    body=json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1024,
        "messages": [{"role": "user", "content": prompt}]
    })
)
```

- **Multi-Turn:** The Lambda stores conversation history in DynamoDB (keyed by `session_id`). Each subsequent voice input appends to the history, enabling natural multi-turn form filling.
- **Entity Accumulation:** Extracted entities are merged across turns until `form_complete: true`.

#### Step 6 — Text-to-Speech (Amazon Polly)

```python
polly_response = polly_client.synthesize_speech(
    Text=telugu_response_text,
    OutputFormat="mp3",
    VoiceId="Aditi",           # Hindi female voice
    Engine="neural",           # Neural engine for natural speech
    LanguageCode="te-IN"       # Telugu
)
audio_stream = polly_response["AudioStream"]
# Store in S3, return presigned GET URL to frontend
```

- **Telugu Voice:** Uses Polly's `Aditi` voice (Hindi Neural) or SSML with Telugu phonemes.
- **Streaming:** Audio is streamed to the frontend to enable playback before the full file is generated.

#### Step 7 — Frontend Playback

```typescript
// Frontend plays audio response
const audio = new Audio(response.audio_url);
audio.play();

// Simultaneously update UI with extracted entities (visual confirmation)
updateFormPreview(response.extracted_entities);
```

---

## 3. Database Schema (DynamoDB)

All tables use **On-Demand** capacity mode (pay-per-request) to stay within free tier during low-traffic hackathon usage.

### 3.1 UsersTable

| Attribute | Type | Key | Description |
|---|---|---|---|
| `user_id` | `S` (String) | **Partition Key** | UUID v4, generated on first visit |
| `phone_hash` | `S` | — | SHA-256 hash of phone number (optional login) |
| `language_pref` | `S` | — | Preferred language code: `te-IN`, `hi-IN` |
| `location_lat_long` | `S` | — | `"17.385044,78.486671"` (Hyderabad) — used for state-level scheme filtering |
| `persona` | `S` | — | Selected avatar: `farmer`, `student`, `worker`, `senior` |
| `created_at` | `S` | — | ISO 8601 timestamp |
| `last_active` | `S` | — | ISO 8601 timestamp (TTL-eligible for cleanup) |

**Access Patterns:**
- Get user by `user_id` (direct lookup)
- No GSIs needed for the prototype

```json
{
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "phone_hash": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
  "language_pref": "te-IN",
  "location_lat_long": "17.385044,78.486671",
  "persona": "farmer",
  "created_at": "2026-02-15T10:30:00Z",
  "last_active": "2026-02-15T11:45:00Z"
}
```

### 3.2 SchemesTable

| Attribute | Type | Key | Description |
|---|---|---|---|
| `scheme_id` | `S` (String) | **Partition Key** | Slugified ID: `rythu-bandhu`, `aasara-pension` |
| `scheme_name` | `S` | — | Human-readable name: `"Rythu Bandhu Investment Support"` |
| `state` | `S` | — | `"Telangana"`, `"Central"`, `"Andhra Pradesh"` |
| `category` | `S` | — | `"agriculture"`, `"pension"`, `"education"` |
| `eligibility_criteria_vector_id` | `S` | — | Reference ID linking to the Bedrock Knowledge Base chunk |
| `benefits_json` | `S` (JSON string) | — | `{"amount": "₹10,000/acre/year", "frequency": "bi-annual"}` |
| `required_documents` | `L` (List) | — | `["aadhaar", "land_pattadar_passbook", "bank_passbook"]` |
| `form_schema_json` | `S` (JSON string) | — | JSON Schema defining the fields the application form needs |
| `active` | `BOOL` | — | Whether the scheme is currently accepting applications |

**GSI — `StateCategoryIndex`:**
- Partition Key: `state`
- Sort Key: `category`
- Purpose: Filter schemes by user's state (derived from `location_lat_long`) and persona category

```json
{
  "scheme_id": "rythu-bandhu",
  "scheme_name": "Rythu Bandhu Investment Support Scheme",
  "state": "Telangana",
  "category": "agriculture",
  "eligibility_criteria_vector_id": "kb-chunk-0042",
  "benefits_json": "{\"amount\": \"₹10,000/acre/year\", \"frequency\": \"Rabi + Kharif\", \"max_acres\": \"no_limit\"}",
  "required_documents": ["aadhaar", "land_pattadar_passbook", "bank_passbook"],
  "form_schema_json": "{\"fields\": [{\"key\": \"name\", \"type\": \"string\"}, {\"key\": \"age\", \"type\": \"number\"}, {\"key\": \"land_acres\", \"type\": \"number\"}, {\"key\": \"survey_number\", \"type\": \"string\"}, {\"key\": \"bank_account\", \"type\": \"string\"}]}",
  "active": true
}
```

### 3.3 ApplicationsTable

| Attribute | Type | Key | Description |
|---|---|---|---|
| `application_id` | `S` (String) | **Partition Key** | UUID v4, generated when form filling begins |
| `user_id` | `S` (String) | **Sort Key** | References `UsersTable.user_id` |
| `scheme_id` | `S` | — | References `SchemesTable.scheme_id` |
| `status` | `S` | — | Enum: `draft`, `pending_confirmation`, `submitted`, `approved`, `rejected` |
| `form_data_json` | `S` (JSON string) | — | The AI-filled form: `{"name": "Ramaiah", "age": 45, ...}` |
| `conversation_history` | `L` (List) | — | Array of `{role, content, timestamp}` objects from the voice session |
| `created_at` | `S` | — | ISO 8601 timestamp |
| `updated_at` | `S` | — | ISO 8601 timestamp |
| `submitted_at` | `S` | — | ISO 8601 timestamp (null if not yet submitted) |

**GSI — `UserApplicationsIndex`:**
- Partition Key: `user_id`
- Sort Key: `created_at`
- Purpose: Fetch all applications for a given user, sorted by date

```json
{
  "application_id": "f1e2d3c4-b5a6-7890-fedc-ba0987654321",
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "scheme_id": "rythu-bandhu",
  "status": "pending_confirmation",
  "form_data_json": "{\"name\": \"Ramaiah Goud\", \"age\": 45, \"income\": 120000, \"land_acres\": 3.5, \"survey_number\": \"123/4A\", \"bank_account\": \"XXXX-XXXX-1234\"}",
  "conversation_history": [
    {"role": "user", "content": "నాకు రైతు బంధు కావాలి", "timestamp": "2026-02-15T10:30:00Z"},
    {"role": "assistant", "content": "మీ పేరు చెప్పండి", "timestamp": "2026-02-15T10:30:03Z"},
    {"role": "user", "content": "రామయ్య గౌడ్", "timestamp": "2026-02-15T10:30:10Z"}
  ],
  "created_at": "2026-02-15T10:30:00Z",
  "updated_at": "2026-02-15T10:35:00Z",
  "submitted_at": null
}
```

### 3.4 SessionsTable (Conversation State)

| Attribute | Type | Key | Description |
|---|---|---|---|
| `session_id` | `S` (String) | **Partition Key** | UUID v4 per voice session |
| `user_id` | `S` | — | References `UsersTable.user_id` |
| `accumulated_entities` | `S` (JSON) | — | Merged entities across turns: `{"name": "Ramaiah", "age": 45}` |
| `current_scheme_id` | `S` | — | The scheme being discussed |
| `turn_count` | `N` | — | Number of voice turns in this session |
| `ttl` | `N` | — | DynamoDB TTL — auto-expire after 1 hour (3600s from creation) |

---

## 4. API Design (FastAPI Interface)

### 4.1 Base Configuration

```python
# app/main.py
from fastapi import FastAPI
from mangum import Mangum

app = FastAPI(
    title="Jan-Sahayak API",
    version="1.0.0",
    description="Voice-First Government Scheme Assistant"
)

# Lambda handler
handler = Mangum(app, lifespan="off")
```

### 4.2 Core Endpoints

---

#### `POST /api/v1/process-voice`

**Purpose:** Main pipeline handler — receives audio reference, runs the full Voice-to-Action pipeline, returns audio response + extracted entities.

**Request:**
```json
{
  "s3_key": "audio/a1b2c3d4/1708012345.webm",
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "session_id": "s1e2s3s4-i5o6-n7890-abcd-ef1234567890",
  "language": "te-IN"
}
```

**Response (200 OK):**
```json
{
  "audio_url": "https://jansahayak-audio.s3.amazonaws.com/response/a1b2c3d4/resp_171234.mp3?X-Amz-Signature=...",
  "response_text": "రైతు బంధు పథకంలో మీకు సంవత్సరానికి ₹10,000 ఎకరానికి లభిస్తుంది. మీ పేరు చెప్పండి.",
  "extracted_entities": {
    "intent": "apply_scheme",
    "scheme_id": "rythu-bandhu",
    "name": null,
    "age": null
  },
  "form_complete": false,
  "next_question": "What is your full name?",
  "session_id": "s1e2s3s4-i5o6-n7890-abcd-ef1234567890"
}
```

**Error Responses:**

| Code | Scenario |
|---|---|
| `400` | Missing `s3_key` or `user_id` |
| `408` | Transcription timed out (> 10s) |
| `422` | Audio format unsupported |
| `500` | Bedrock / Polly service error |

---

#### `GET /api/v1/schemes/recommended`

**Purpose:** Returns a list of government schemes relevant to the user based on their location (state) and persona.

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | Yes | User ID to look up profile |
| `limit` | int | No | Max results (default: 5) |

**Response (200 OK):**
```json
{
  "schemes": [
    {
      "scheme_id": "rythu-bandhu",
      "scheme_name": "Rythu Bandhu Investment Support Scheme",
      "category": "agriculture",
      "benefit_summary": "₹10,000 per acre per year",
      "audio_summary_url": "https://jansahayak-audio.s3.amazonaws.com/schemes/rythu-bandhu-te.mp3"
    },
    {
      "scheme_id": "aasara-pension",
      "scheme_name": "Aasara Pension Scheme",
      "category": "pension",
      "benefit_summary": "₹2,016 per month",
      "audio_summary_url": "https://jansahayak-audio.s3.amazonaws.com/schemes/aasara-pension-te.mp3"
    }
  ],
  "total": 2
}
```

---

#### `POST /api/v1/application/submit`

**Purpose:** Submits the AI-generated, user-confirmed JSON form as a formal application.

**Request:**
```json
{
  "application_id": "f1e2d3c4-b5a6-7890-fedc-ba0987654321",
  "user_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "scheme_id": "rythu-bandhu",
  "form_data": {
    "name": "Ramaiah Goud",
    "age": 45,
    "annual_income": 120000,
    "land_acres": 3.5,
    "survey_number": "123/4A",
    "bank_account_last4": "1234",
    "caste_category": "OBC"
  },
  "confirmed_via_voice": true
}
```

**Response (201 Created):**
```json
{
  "application_id": "f1e2d3c4-b5a6-7890-fedc-ba0987654321",
  "status": "submitted",
  "submitted_at": "2026-02-15T10:40:00Z",
  "confirmation_audio_url": "https://jansahayak-audio.s3.amazonaws.com/confirm/f1e2d3c4.mp3",
  "message": "Your application for Rythu Bandhu has been submitted successfully."
}
```

---

#### `GET /api/v1/presigned-upload-url`

**Purpose:** Returns a presigned S3 PUT URL for the frontend to upload audio blobs directly.

**Query Parameters:**

| Param | Type | Required | Description |
|---|---|---|---|
| `user_id` | string | Yes | Used to namespace the S3 key |
| `content_type` | string | No | MIME type (default: `audio/webm`) |

**Response (200 OK):**
```json
{
  "upload_url": "https://jansahayak-audio.s3.amazonaws.com/audio/a1b2c3d4/1708012345.webm?X-Amz-Signature=...",
  "s3_key": "audio/a1b2c3d4/1708012345.webm",
  "expires_in": 300
}
```

---

### 4.3 Pydantic Models

```python
# app/models.py
from pydantic import BaseModel
from typing import Optional
from enum import Enum

class LanguageCode(str, Enum):
    TELUGU = "te-IN"
    HINDI = "hi-IN"

class ProcessVoiceRequest(BaseModel):
    s3_key: str
    user_id: str
    session_id: Optional[str] = None
    language: LanguageCode = LanguageCode.TELUGU

class ExtractedEntities(BaseModel):
    intent: Optional[str] = None
    scheme_id: Optional[str] = None
    name: Optional[str] = None
    age: Optional[int] = None
    income: Optional[float] = None
    land_acres: Optional[float] = None
    caste_category: Optional[str] = None
    survey_number: Optional[str] = None

class ProcessVoiceResponse(BaseModel):
    audio_url: str
    response_text: str
    extracted_entities: ExtractedEntities
    form_complete: bool
    next_question: Optional[str] = None
    session_id: str

class ApplicationSubmitRequest(BaseModel):
    application_id: str
    user_id: str
    scheme_id: str
    form_data: dict
    confirmed_via_voice: bool = False
```

---

## 5. Security & Optimization

### 5.1 PII Handling — Aadhaar Number Protection

Indian Aadhaar numbers (12-digit unique IDs) are classified as **Sensitive PII** under the Digital Personal Data Protection Act (DPDPA) 2023. Jan-Sahayak **never** sends raw Aadhaar numbers to the LLM.

**Implementation — AWS-Native PII Detection (Amazon Comprehend):**

Instead of relying on custom Regex (which is brittle and may miss edge cases), we use **Amazon Comprehend** — a fully managed NLP service that automatically detects PII entity types (Aadhaar, Phone, Address, etc.) with ML-based accuracy.

```python
import boto3

comprehend = boto3.client('comprehend', region_name='ap-south-1')

def detect_and_mask_pii(text: str) -> tuple[str, dict]:
    """
    Uses Amazon Comprehend to detect ALL PII entities (Aadhaar, Phone, etc.)
    and masks them before sending text to Bedrock.
    Returns sanitized text and a mapping for later reconstruction.
    """
    response = comprehend.detect_pii_entities(
        Text=text,
        LanguageCode='en'
    )

    pii_map = {}
    masked_text = text

    # Process entities in reverse order to preserve character offsets
    for entity in sorted(response['Entities'], key=lambda e: e['BeginOffset'], reverse=True):
        entity_type = entity['Type']       # e.g., 'AADHAAR_NUMBER', 'PHONE', 'ADDRESS'
        start = entity['BeginOffset']
        end = entity['EndOffset']
        original_value = text[start:end]

        token = f"[{entity_type}_{len(pii_map)}]"
        pii_map[token] = original_value
        masked_text = masked_text[:start] + token + masked_text[end:]

    return masked_text, pii_map

def restore_pii(text: str, pii_map: dict) -> str:
    """Restores PII tokens in the final form data (never in LLM context)."""
    for token, original in pii_map.items():
        text = text.replace(token, original)
    return text
```

**Why Amazon Comprehend over Custom Regex?**

| Aspect | Custom Regex | Amazon Comprehend |
|---|---|---|
| **Coverage** | Only catches patterns you explicitly write | Detects 30+ PII types (Aadhaar, PAN, Passport, Phone, Address, Bank A/C) |
| **Accuracy** | Misses edge cases (e.g., `1234-5678-9012` vs `123456789012`) | ML-based detection handles all formats |
| **Maintenance** | Must update regex for new PII types | AWS manages model updates |
| **Hackathon Points** | Basic implementation | Extra "AWS Service Usage" points from judges |

**Flow:**
1. User says: *"My Aadhaar is 1234 5678 9012"*
2. Transcribe outputs: `"My Aadhaar is 1234 5678 9012"`
3. `detect_and_mask_pii()` → Amazon Comprehend detects `AADHAAR_NUMBER` → Sends `"My Aadhaar is [AADHAAR_NUMBER_0]"` to Bedrock
4. Bedrock extracts: `{"aadhaar": "[AADHAAR_NUMBER_0]"}`
5. `restore_pii()` → Final form JSON contains `"aadhaar": "1234 5678 9012"` (stored encrypted in DynamoDB)
6. **PII is NEVER logged, NEVER sent to LLM in plaintext**

**Additional PII Measures:**
- Audio blobs are auto-deleted from S3 after 24 hours (S3 Lifecycle Policy)
- DynamoDB stores phone numbers as SHA-256 hashes only
- All API responses strip Aadhaar from `response_text` before TTS
- Bank account numbers are masked to last 4 digits in conversation: `XXXX-XXXX-1234`

### 5.2 Latency Optimization — 2G Network Support

Target: **Voice-to-Voice response in < 3 seconds on 4G, < 8 seconds on 2G.**

| Optimization | Technique | Impact |
|---|---|---|
| **Audio Streaming** | Polly returns `AudioStream` (chunked transfer encoding); frontend plays via `MediaSource` API as bytes arrive | First audio heard in ~500ms instead of waiting for full file |
| **Transcribe Streaming** | Use WebSocket-based `StartStreamTranscription` instead of batch `StartTranscriptionJob` | Saves ~3s (no S3 round-trip for batch) |
| **Compressed Audio** | Record at 16kHz mono (Opus codec in WebM) — ~32kbps vs. 256kbps for WAV | 8x smaller upload for 2G |
| **PWA Caching** | Service Worker caches: cartoon SVGs, pre-recorded scheme name audio, UI shell | Zero network for static assets after first load |
| **Edge Caching** | API Gateway response caching (30s TTL) for `/schemes/recommended` | Repeated scheme lookups served from cache |
| **Lambda Warm Pool** | Provisioned concurrency = 1 keeps one Lambda instance warm | Eliminates ~800ms cold start |
| **Connection Pooling** | Reuse `boto3` clients across invocations (declared outside handler) | Saves ~200ms per AWS SDK call |

**2G Fallback Strategy:**
```
If network speed < 50kbps (detected via Navigator.connection API):
  → Switch to "Lite Mode"
  → Disable audio streaming, use pre-cached audio clips
  → Show loading animation with cartoon character
  → Queue voice input for batch processing
```

### 5.3 Cost Optimization — AWS Free Tier Strategy

Jan-Sahayak is designed to run **entirely within AWS Free Tier** for the hackathon prototype (estimated ~100 users/day).

| Service | Free Tier Allowance | Our Estimated Usage | Under Limit? |
|---|---|---|---|
| **Lambda** | 1M requests + 400,000 GB-s/month | ~3,000 requests × 0.5 GB × 3s = 4,500 GB-s | ✅ Yes |
| **API Gateway** | 1M HTTP API calls/month | ~3,000 calls | ✅ Yes |
| **DynamoDB** | 25 GB storage + 25 WCU + 25 RCU | < 1 GB, On-Demand ~100 WCU/day | ✅ Yes |
| **S3** | 5 GB storage + 20,000 GET + 2,000 PUT | < 2 GB audio (auto-deleted), ~500 PUTs | ✅ Yes |
| **Transcribe** | 60 min/month (first 12 months) | ~50 min (100 users × 30s each) | ✅ Yes |
| **Polly** | 5M characters/month (first 12 months) | ~200K chars (100 users × 2K chars) | ✅ Yes |
| **Translate** | 2M characters/month (first 12 months) | ~150K chars | ✅ Yes |
| **Bedrock** | Pay-per-token (no free tier) | ~$2-5/day at prototype scale | ⚠️ Paid |

**Cost Mitigation for Bedrock:**
- Use **Claude 3 Haiku** for simple intent classification (10x cheaper than Sonnet)
- Use **Claude 3 Sonnet** only for complex entity extraction and form filling
- Cache common scheme queries in DynamoDB to avoid redundant Bedrock calls
- Set a **hard spending limit** of $10/day via AWS Budgets alarm

**Estimated Total Monthly Cost:** < ₹500 (~$6) for prototype usage.

### 5.4 Infrastructure as Code

All AWS resources are defined in **AWS SAM (Serverless Application Model)** for one-command deployment:

```yaml
# template.yaml (SAM)
AWSTemplateFormatVersion: '2010-09-09'
Transform: AWS::Serverless-2016-10-31

Globals:
  Function:
    Timeout: 29
    MemorySize: 512
    Runtime: python3.12
    Architectures: [arm64]

Resources:
  JanSahayakFunction:
    Type: AWS::Serverless::Function
    Properties:
      Handler: app.main.handler
      Events:
        ApiEvent:
          Type: HttpApi
          Properties:
            ApiId: !Ref JanSahayakApi

  JanSahayakApi:
    Type: AWS::Serverless::HttpApi
    Properties:
      StageName: prod
      CorsConfiguration:
        AllowOrigins: ["https://jansahayak.vercel.app"]
        AllowMethods: ["GET", "POST", "OPTIONS"]
        AllowHeaders: ["Content-Type", "Authorization"]

  UsersTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: JanSahayak-Users
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: user_id
          AttributeType: S
      KeySchema:
        - AttributeName: user_id
          KeyType: HASH

  SchemesTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: JanSahayak-Schemes
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: scheme_id
          AttributeType: S
        - AttributeName: state
          AttributeType: S
        - AttributeName: category
          AttributeType: S
      KeySchema:
        - AttributeName: scheme_id
          KeyType: HASH
      GlobalSecondaryIndexes:
        - IndexName: StateCategoryIndex
          KeySchema:
            - AttributeName: state
              KeyType: HASH
            - AttributeName: category
              KeyType: RANGE
          Projection:
            ProjectionType: ALL

  ApplicationsTable:
    Type: AWS::DynamoDB::Table
    Properties:
      TableName: JanSahayak-Applications
      BillingMode: PAY_PER_REQUEST
      AttributeDefinitions:
        - AttributeName: application_id
          AttributeType: S
        - AttributeName: user_id
          AttributeType: S
        - AttributeName: created_at
          AttributeType: S
      KeySchema:
        - AttributeName: application_id
          KeyType: HASH
        - AttributeName: user_id
          KeyType: RANGE
      GlobalSecondaryIndexes:
        - IndexName: UserApplicationsIndex
          KeySchema:
            - AttributeName: user_id
              KeyType: HASH
            - AttributeName: created_at
              KeyType: RANGE
          Projection:
            ProjectionType: ALL

  AudioBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: jansahayak-audio
      LifecycleConfiguration:
        Rules:
          - Id: DeleteTempAudio
            Prefix: audio/
            Status: Enabled
            ExpirationInDays: 1

  DocsBucket:
    Type: AWS::S3::Bucket
    Properties:
      BucketName: jansahayak-docs
```

**Deploy Command:**
```bash
sam build && sam deploy --guided
```

---

> **Document Version:** 1.0  
> **Last Updated:** 2026-02-15  
> **Authors:** Jan-Sahayak Team — AI for Bharat Hackathon
