import axios from 'axios';

const API_BASE = "https://ai-for-bharat1.up.railway.app";

const apiClient = axios.create({
    baseURL: API_BASE,
});

export interface TranscribeResponse {
    success: boolean;
    text: string;
    english_text?: string;
    user_language?: string;
    detected_language?: string;
    duration_seconds?: number;
    model_used: string;
    message?: string;
}

export interface ChatResponse {
    success: boolean;
    reply: string;
    new_state: string;
    form_data: Record<string, string>;
    audio_base64: string;
}

export const Api = {
    /**
     * Authenticate or create a user by their mobile number.
     * Returns the DynamoDB session_id to be used in future Bedrock chats.
     */
    async login(mobileNumber: string): Promise<{ session_id: string; is_new_user: boolean }> {
        const response = await apiClient.post("/api/v1/auth/login", {
            mobile_number: mobileNumber
        });
        return response.data;
    },

    /**
     * Transcribe an audio Blob using the backend Groq Whisper endpoint.
     */
    async transcribe(
        audioBlob: Blob,
        filename = "recording.webm",
        language = ""
    ): Promise<TranscribeResponse> {
        const form = new FormData();
        form.append("audio", audioBlob, filename);
        if (language) form.append("language", language);

        const response = await apiClient.post<TranscribeResponse>(
            "/api/v1/voice/transcribe",
            form,
            {
                headers: { "Content-Type": "multipart/form-data" },
                timeout: 15000
            }
        );

        return response.data;
    },

    /**
     * Send the translated English text to the Bedrock AI Chat system.
     * Receives the AI's translated reply and the Polly Base64 Audio buffer.
     */
    async sendChatMessage(sessionId: string, message: string, userLanguage: string): Promise<ChatResponse> {
        const response = await apiClient.post<ChatResponse>(
            "/api/v1/chat/message",
            { message: message, user_language: userLanguage },
            {
                headers: {
                    "X-Session-Id": sessionId,
                    "Content-Type": "application/json"
                }
            }
        );
        return response.data;
    },

    /**
     * Admin: Get all applications
     */
    async getAdminApplications(): Promise<any[]> {
        const response = await apiClient.get("/api/v1/admin/applications");
        return response.data.data;
    },

    /**
     * Admin: Update application status
     */
    async updateAdminApplicationStatus(id: string, status: string, reason: string): Promise<boolean> {
        const response = await apiClient.post(`/api/v1/admin/applications/${id}/status`, {
            status,
            reason
        });
        return response.data.success;
    },

    /**
     * Health check
     */
    async healthCheck() {
        const response = await apiClient.get("/health");
        return response.data;
    }
};
