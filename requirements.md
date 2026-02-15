# Requirements Document - Jan-Sahayak

## 1. Project Overview
**Jan-Sahayak** is a Voice-First, Text-Free Progressive Web Application (PWA) designed to bridge the digital literacy gap for India's 300+ million illiterate citizens. The system enables users to access government schemes and automatically fill application forms through voice interactions in local dialects (Telugu/Hindi), eliminating the need for reading or writing skills.

## 2. Problem Statement
India has over 300 million illiterate citizens who cannot access digital government services due to text-based interfaces. These citizens, primarily farmers and daily wage workers, miss out on critical government schemes (like Rythu Bandhu or Aasara Pensions) because they cannot navigate complex online forms or understand English eligibility criteria.

## 3. Scope of Work

### In-Scope
* **Text-Free UI:** Visual navigation using semi-abstracted cartoons (Farmer, Student, Worker).
* **Voice-First Interaction:** Full duplex voice conversation in Telugu and Hindi.
* **RAG-based Discovery:** Zero-hallucination scheme search using official Government PDFs.
* **Actionable AI (Form Filling):** Automated extraction of user details to fill JSON application forms.
* **Offline Audio Mode:** Cached audio responses for low-bandwidth (2G) areas.

### Out-of-Scope
* Biometric authentication (Fingerprint/Iris).
* Real-time payment gateway integration.
* Physical document scanning/verification (for this prototype phase).
* Video calling support.

## 4. Functional Requirements

### Requirement 1: Voice-Based Identity Selection
**User Story:** As an illiterate user, I want to select my identity using cartoons, so I do not have to read text labels.
* **Criteria:** System must display large, clickable avatars (e.g., Farmer with Tractor).
* **Criteria:** On clicking, the avatar must "speak" its name (Audio-on-Hover).

### Requirement 2: Multilingual Voice Support
**User Story:** As a Telugu speaker, I want to speak naturally without knowing English commands.
* **Criteria:** Input audio must be transcribed using **AWS Transcribe** (supports Telugu/Hindi).
* **Criteria:** Output text must be converted to lifelike speech using **AWS Polly**.
* **Criteria:** System must handle mixed-language input (Code-switching) via **AWS Translate**.

### Requirement 3: Zero-Hallucination Scheme Discovery
**User Story:** As a user, I need accurate information about government rules, not AI guesses.
* **Criteria:** The system must use **AWS Bedrock Knowledge Bases** to retrieve answers *only* from uploaded Government PDFs.
* **Criteria:** If the answer is not in the PDF, the AI must clearly state "I do not know."

### Requirement 4: Automated Form Filling (The "Action Agent")
**User Story:** As a user who cannot write, I want the AI to fill the application form for me.
* **Criteria:** The AI (Claude 3 Sonnet) must extract entities (Name, Age, Income, Land Size) from the conversation.
* **Criteria:** The system must generate a structured **JSON payload** matching the government portal's schema.
* **Criteria:** The system must verbally confirm the details before submission.

### Requirement 5: Low-Bandwidth Performance
**User Story:** As a villager with 2G internet, I need the app to work without freezing.
* **Criteria:** The app must stream audio responses (chunked transfer) to reduce latency.
* **Criteria:** Static assets (Cartoons, Icons) must be cached via Service Workers (PWA).

## 5. Non-Functional Requirements
* **Latency:** Voice-to-Voice response time < 3 seconds on 4G networks.
* **Accuracy:** Speech-to-Text accuracy > 85% for rural dialects.
* **Reliability:** 99.9% uptime during business hours (Serverless architecture).
* **Privacy:** No PII (Personally Identifiable Information) stored permanently; Audio deleted immediately after processing.

## 6. Technical Stack Requirements

### Frontend (The Interface)
* **Framework:** Next.js 14 (React) with TypeScript.
* **Styling:** Tailwind CSS (Mobile-first design).
* **PWA:** Service Workers for offline capabilities.
* **Audio:** Native MediaRecorder API for capturing voice.

### Backend (The Logic)
* **Compute:** **AWS Lambda** (Serverless Python functions).
* **Framework:** FastAPI (wrapped in Mangum adapter for Lambda).
* **Orchestration:** AWS Step Functions (optional) for complex workflows.

### AI & Data (The Brain)
* **LLM:** **Amazon Bedrock** (Model: Claude 3 Sonnet or Haiku).
* **RAG Engine:** **Amazon Bedrock Knowledge Bases** (Managed Vector Search).
* **Speech Services:** Amazon Transcribe (ASR), Amazon Polly (TTS), Amazon Translate.
* **Database:** **Amazon DynamoDB** (Serverless NoSQL) for User Profiles and Application Logs.
* **Storage:** **Amazon S3** for storing Government Scheme PDFs and temporary audio blobs.

## 7. Success Criteria
* Successfully helping a user find a scheme (e.g., Rythu Bandhu) using *only* voice.
* Successfully generating a filled JSON application form from a voice conversation.
* Deployment on AWS Free Tier with < ₹100 estimated cost.