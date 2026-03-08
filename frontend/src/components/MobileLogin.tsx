import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Loader2, AlertCircle, Phone } from "lucide-react";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { Api } from "../services/api";

import { t } from "../i18n";

interface MobileLoginProps {
    onLoginSuccess: (sessionId: string, language: string) => void;
    currentLang: string;
    onLanguageChange: (lang: string) => void;
}

export function MobileLogin({ onLoginSuccess, currentLang, onLanguageChange }: MobileLoginProps) {
    const {
        status,
        errorMessage,
        result,
        visualiserData,
        language,
        setLanguage,
        toggleRecording,
        setErrorMessage,
    } = useVoiceRecorder(null, false, currentLang);

    // Sync local hook state to global App state when user changes dropdown
    useEffect(() => {
        onLanguageChange(language);
    }, [language, onLanguageChange]);

    const [isLoggingIn, setIsLoggingIn] = useState(false);

    // Filter out non-numeric characters to try and catch a phone number
    const extractedNumber = result?.text.replace(/\D/g, "") || "";

    const handleLoginSubmit = async () => {
        if (extractedNumber.length < 10) {
            setErrorMessage("Please provide a valid 10-digit mobile number.");
            return;
        }

        setIsLoggingIn(true);
        try {
            const loginResp = await Api.login(extractedNumber);
            onLoginSuccess(loginResp.session_id, language);
        } catch (err: any) {
            console.error("Login failed:", err);
            setErrorMessage(err.response?.data?.detail || "Failed to login. Please try again.");
            setIsLoggingIn(false);
        }
    };

    const isListening = status === "listening";
    const isProcessing = status === "processing" || isLoggingIn;

    return (
        <div className="voice-recorder-card">
            {/* ── Title ── */}
            <div className="text-center mb-6">
                <h2 style={{ color: "white", fontSize: "1.5rem", marginBottom: "0.5rem" }}>{t('welcome_title', language)}</h2>
                <p style={{ color: "#a1a1aa", fontSize: "0.95rem" }}>{t('welcome_subtitle', language)}</p>
            </div>

            {/* ── Language Selector ── */}
            <div className="language-section" style={{ marginBottom: "2rem" }}>
                <label className="section-label" htmlFor="language-select">{t('speak_in', language)}</label>
                <select
                    id="language-select"
                    className="language-select"
                    value={language}
                    onChange={(e) => setLanguage(e.target.value)}
                >
                    <option value="">Auto Detect</option>
                    <option value="hi">Hindi — हिंदी</option>
                    <option value="en">English</option>
                    <option value="ta">Tamil — தமிழ்</option>
                    <option value="te">Telugu — తెలుగు</option>
                    <option value="mr">Marathi — मराठी</option>
                    <option value="bn">Bengali — বাংলা</option>
                </select>
            </div>

            {/* ── Mic Button & Visualiser ── */}
            <div className="mic-section">
                <div className="visualiser-container">
                    {visualiserData.map((h, i) => (
                        <motion.div
                            key={i}
                            className="visualiser-bar"
                            animate={{ height: isListening ? h : 8 }}
                            transition={{ type: "tween", duration: 0.1 }}
                        />
                    ))}
                </div>

                <motion.button
                    onClick={toggleRecording}
                    disabled={isProcessing}
                    whileHover={!isProcessing ? { scale: 1.05 } : {}}
                    whileTap={!isProcessing ? { scale: 0.95 } : {}}
                    className={`mic-btn ${isListening ? "mic-recording" : ""} ${isProcessing ? "mic-processing" : ""}`}
                    animate={{
                        boxShadow: isListening
                            ? ["0 0 0 0 rgba(239,68,68,0.4)", "0 0 0 16px rgba(239,68,68,0)"]
                            : "0 0 0 0 rgba(249,115,22,0)",
                    }}
                    transition={{ boxShadow: { duration: 1.4, repeat: Infinity } }}
                >
                    {isProcessing ? <Loader2 className="processing-icon animate-spin" /> : <Mic className="mic-icon" />}
                </motion.button>
                <span className="mic-label">
                    {isListening ? t('listening', language) : t('tap_mic_number', language)}
                </span>
            </div>

            {/* ── Result & Confirm Action ── */}
            <AnimatePresence>
                {result && (
                    <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: "auto" }}
                        className="result-section"
                        style={{ marginTop: "2rem" }}
                    >
                        <div className="result-box result-has-content text-center">
                            <span style={{ fontSize: "1.2rem", letterSpacing: "2px" }}>
                                {extractedNumber || result.text}
                            </span>
                        </div>

                        {extractedNumber.length >= 10 && (
                            <motion.button
                                initial={{ scale: 0.9, opacity: 0 }}
                                animate={{ scale: 1, opacity: 1 }}
                                className="w-full mt-4 flex items-center justify-center gap-2"
                                style={{
                                    background: "linear-gradient(135deg, #10b981 0%, #059669 100%)",
                                    color: "white", padding: "12px 24px", borderRadius: "12px",
                                    fontWeight: 600, border: "none", cursor: "pointer", width: "100%", marginTop: "1rem"
                                }}
                                onClick={handleLoginSubmit}
                                disabled={isLoggingIn}
                            >
                                {isLoggingIn ? <Loader2 className="animate-spin" /> : <Phone size={20} />}
                                {isLoggingIn ? t('logging_in', language) : t('confirm_btn', language)}
                            </motion.button>
                        )}
                    </motion.div>
                )}
            </AnimatePresence>

            {/* ── Error Toast ── */}
            <AnimatePresence>
                {errorMessage && (
                    <motion.div
                        initial={{ opacity: 0, y: 50, x: "-50%" }}
                        animate={{ opacity: 1, y: 0, x: "-50%" }}
                        exit={{ opacity: 0, y: 50, x: "-50%" }}
                        className="error-toast"
                    >
                        <AlertCircle className="toast-icon" />
                        <span className="toast-text">{errorMessage}</span>
                        <button onClick={() => setErrorMessage(null)} className="toast-close">✕</button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
