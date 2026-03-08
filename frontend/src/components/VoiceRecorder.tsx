import React, { useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mic, Loader2, AlertCircle } from "lucide-react";
import { useVoiceRecorder } from "../hooks/useVoiceRecorder";
import { t } from "../i18n";
import "./VoiceRecorder.css";

interface VoiceRecorderProps {
    sessionId: string;
    initialLang: string;
    onLanguageChange: (lang: string) => void;
}

export function VoiceRecorder({ sessionId, initialLang, onLanguageChange }: VoiceRecorderProps) {
    const {
        status,
        errorMessage,
        result,
        chatReply,
        visualiserData,
        language,
        setLanguage,
        toggleRecording,
        autoGreet,
        setErrorMessage,
    } = useVoiceRecorder(sessionId, true, initialLang);

    // Sync local hook state to global App state when user changes dropdown
    useEffect(() => {
        onLanguageChange(language);
    }, [language, onLanguageChange]);

    // Request auto-greeting on mount, protected against React 18 Strict Mode double-invocation
    const hasGreeted = React.useRef(false);
    useEffect(() => {
        if (!hasGreeted.current) {
            hasGreeted.current = true;
            autoGreet();
        }
    }, [autoGreet]);

    // Status mapping
    const statusConfig = {
        idle: { dotCls: "dot-idle", text: t('tap_mic_speak', initialLang), icon: null },
        listening: { dotCls: "dot-listening", text: t('listening', initialLang), icon: null },
        processing: {
            dotCls: "dot-processing",
            text: "⏳ AI is thinking...",
            icon: <Loader2 className="processing-icon" />,
        },
        playing: { dotCls: "dot-success", text: "🔊 Didi is speaking...", icon: null },
        success: { dotCls: "dot-success", text: "✅ Finished", icon: null },
        error: { dotCls: "dot-error", text: "❌ Error occurred", icon: null },
    };

    const isListening = status === "listening";
    const isProcessing = status === "processing";
    const currentStatus = statusConfig[status];

    return (
        <div className="voice-recorder-card">
            {/* ── Status Banner ── */}
            <motion.div
                layout
                className={`status-banner ${isListening ? "status-listening" : ""}`}
            >
                <div className={`status-dot ${currentStatus.dotCls}`} />
                <span>
                    {currentStatus.icon}
                    {currentStatus.text}
                </span>
            </motion.div>

            {/* ── Active Session Meta ── */}
            <div className="language-section" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
                <span className="section-label" style={{ margin: 0 }}>📍 Session Active</span>
                <select
                    className="language-select"
                    style={{ background: 'rgba(255,255,255,0.1)', padding: '4px 12px', borderRadius: '16px', fontSize: '0.9rem', color: '#a1a1aa', border: 'none', appearance: 'auto' }}
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
                {/* Visualiser */}
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

                {/* Mic Button */}
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
                    transition={{
                        boxShadow: {
                            duration: 1.4,
                            repeat: Infinity,
                        },
                    }}
                >
                    <Mic className="mic-icon" />
                </motion.button>
                <span className="mic-label">
                    {isListening ? t('listening', initialLang) : t('tap_mic_speak', initialLang)}
                </span>
            </div>

            {/* ── Result Box ── */}
            <div className="result-section">
                <label className="section-label">{t('detected_text', initialLang)}</label>
                <motion.div
                    layout
                    className={`result-box ${result ? "result-has-content" : ""}`}
                >
                    <AnimatePresence mode="popLayout">
                        {result ? (
                            <motion.span
                                key="result"
                                initial={{ opacity: 0, y: 5 }}
                                animate={{ opacity: 1, y: 0 }}
                                exit={{ opacity: 0 }}
                            >
                                {result.text}
                            </motion.span>
                        ) : (
                            <motion.span key="placeholder" className="result-placeholder">
                                {t('placeholder_text', initialLang)}
                            </motion.span>
                        )}
                    </AnimatePresence>
                </motion.div>

                {/* ── English Translation Box ── */}
                <AnimatePresence>
                    {result?.english_text && result.user_language !== 'en' && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="translation-section"
                        >
                            <label className="section-label" style={{ marginTop: '1rem' }}>{t('english_translation', initialLang)}</label>
                            <div className="result-box result-has-content translation-box">
                                {result.english_text}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ── Didi AI Response Box ── */}
                <AnimatePresence>
                    {chatReply && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="didi-reply-section"
                        >
                            <label className="section-label" style={{ marginTop: '1rem', color: '#6ee7b7' }}>🤖 Didi's Answer</label>
                            <div className="result-box result-has-content" style={{ borderColor: 'var(--primary)', backgroundColor: 'rgba(239, 68, 68, 0.05)' }}>
                                {chatReply.reply}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* ── Live Form Data Panel ── */}
                <AnimatePresence>
                    {chatReply && chatReply.new_state !== "IDLE" && chatReply.new_state !== "SCHEME_DISCUSSION" && (
                        <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="live-form-section"
                            style={{ marginTop: '2rem', padding: '1rem', background: 'rgba(255,255,255,0.03)', borderRadius: '16px', border: '1px solid rgba(255,255,255,0.1)' }}
                        >
                            <label className="section-label" style={{ color: '#60a5fa', display: 'flex', alignItems: 'center', gap: '8px' }}>
                                📋 Live Application Form
                            </label>

                            <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem', marginTop: '1rem' }}>
                                {Object.entries(chatReply.form_data || {}).length === 0 ? (
                                    <div style={{ textAlign: 'center', color: '#a1a1aa', padding: '1rem', fontSize: '0.9rem' }}>
                                        Listening for your details...
                                    </div>
                                ) : (
                                    Object.entries(chatReply.form_data).map(([key, val]) => (
                                        <motion.div
                                            key={key}
                                            initial={{ x: -10, opacity: 0 }}
                                            animate={{ x: 0, opacity: 1 }}
                                            style={{
                                                display: 'flex',
                                                justifyContent: 'space-between',
                                                padding: '12px 16px',
                                                background: 'rgba(16, 185, 129, 0.1)',
                                                border: '1px solid rgba(16, 185, 129, 0.3)',
                                                borderRadius: '12px'
                                            }}
                                        >
                                            <span style={{ color: '#a1a1aa', textTransform: 'capitalize' }}>{key.replace('_', ' ')}</span>
                                            <span style={{ color: '#10b981', fontWeight: 600 }}>{val as string}</span>
                                        </motion.div>
                                    ))
                                )}
                            </div>
                        </motion.div>
                    )}
                </AnimatePresence>

                {/* Result Meta */}
                {result && (
                    <motion.div
                        initial={{ opacity: 0 }}
                        animate={{ opacity: 1 }}
                        className="result-meta"
                        style={{ marginTop: '0.5rem' }}
                    >
                        {result.user_language && (
                            <span className="meta-item">🌐 Language: {result.user_language.toUpperCase()}</span>
                        )}
                        {result.detected_language && (
                            <span className="meta-item">🤖 Model: {result.detected_language}</span>
                        )}
                        {result.duration_seconds && (
                            <span className="meta-item">⏱ {result.duration_seconds.toFixed(1)}s</span>
                        )}
                    </motion.div>
                )}
            </div>

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
                        <button
                            onClick={() => setErrorMessage(null)}
                            className="toast-close"
                        >
                            ✕
                        </button>
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
